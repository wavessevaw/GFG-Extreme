"""Service integration for the HUD-only benchmark; one owner of all power writes."""
import copy
import time
from .benchmark import AdaptiveBenchmark, summarize
from .policy import Policy
from . import filters
from .pilot import ladder

class BenchmarkSession:
    def __init__(self, service):
        self.s = service
        self.b = AdaptiveBenchmark()
        self.seq = None
        self.saved = None
        self.validating = False
        self.validation = []
        self.fg_last_seq = None
        self.display_start = None
        self.restore_pending = False
        self.message = ''

    def context(self, st, profile, power, refresh, dock):
        return dict(app=int(st.get('app_id') or 0), refresh=refresh, dock=dock,
                    ac=power.get('external_power'), mode=profile['objective'],
                    post=filters.to_post(profile['filters']), hdr=st.get('transfer'))

    def restore(self):
        if self.saved is None: return
        result=self.s.governor.actuator.restore_if_owned()
        self.restore_pending = result.get('success') is False
        if self.restore_pending:
            self.message='Power restoration pending; retrying'
            return
        self.s.coord.take_over()
        self.s.coord.want(self.saved)
        self.s.coord.tick(self.s.ctl.status())
        self.s.last_policy=self.saved
        self.saved=None
        self.s.pilot.reset()
        self.validating=False

    def abort(self, reason):
        self.b.abort(reason)
        self.message=reason
        self.restore()

    def begin(self, st, profile, ctx, now):
        if self.saved or self.b.active or self.b.phase=='result': return
        if not st.get('fresh') or st.get('steam_ui') or not ctx['app'] or ctx['app']==769:
            self.message='An active game is required'; return
        if st.get('hud_input_version')!=1 or 'native_frame_ms' not in st:
            self.message='Install matching Gamescope runtime'; return
        self.s.boost.stop() if self.s.boost else None
        self.s.split.stop() if self.s.split else None
        self.s.gclock.stop() if self.s.gclock else None
        self.s.governor.stop('benchmark')
        if not self.s._idle_ready():
            self.message='Power restoration must finish first'; return
        actuator=self.s.governor.actuator
        claimed=actuator.claim_at_ceiling_w() if hasattr(actuator,"claim_at_ceiling_w") else actuator.claim()
        if not claimed.get('owned'):
            self.message='Cannot acquire power control'; return
        ceiling=claimed.get('ceiling_tdp_w') or claimed.get('initial_tdp_w')
        floor=max(3,float(claimed.get('minimum_tdp_w') or 3))
        self.saved=self.s.last_policy or Policy()
        try:
            self.b.start(context=ctx,mode=profile['objective'],ceiling=float(ceiling),floor=floor,ladder=ladder(ctx['refresh']),now=now)
            result=actuator.set_tdp_w(self.b.watts)
            if not result.get('success'): raise RuntimeError('TDP write failed')
        except Exception as e:
            self.abort(str(e));return
        self.s.coord.take_over()
        self.message=''

    def tick(self, st, profile, sensors, power, refresh, dock, now):
        ctx=self.context(st,profile,power,refresh,dock)
        seq=st.get('hud_event_seq')
        if self.seq is None: self.seq=seq
        elif seq is not None and seq!=self.seq:
            self.seq=seq
            event=st.get('hud_event')
            if event==1: self.begin(st,profile,ctx,now)
            elif event==2:
                if self.saved: self.abort('Cancelled from HUD')
                else: self.b.phase='idle'
            elif event in (3,4) and self.b.phase=='result' and not self.saved:
                result = self.b.result or {}
                if event==3 and result.get('applicable') and result.get('context')==ctx:
                    record=copy.deepcopy(result)
                    record['user_accepted']=True
                    record['created']=time.time()
                    key=f"{ctx['app']}:{ctx['mode']}:{refresh}:{int(dock)}:{ctx['ac']}"
                    self.s.settings.data.setdefault('benchmarks',{})[key]=record
                    self.s.settings.make_game_profile(ctx['app'])
                    self.s.settings.save()
                    # Re-enter the normal mode-specific Pilot/Governor pipeline now.
                    # The selected TDP is a starting hint, never an unguarded cap.
                    self.s.governor.stop('benchmark-apply')
                    self.s.pilot.reset()
                    self.message=('Applied measured point to '+ctx['mode']+
                                  ' (Governor will adapt)')
                    self.b.phase='idle'
                elif event==3:
                    # A missing sample is not a fake recommendation. Let the
                    # left-hand HUD action retry; only a measured point can Apply.
                    self.b.phase='idle'
                    self.message='No valid measured point; retrying Benchmark'
                    self.begin(st,profile,ctx,now)
                else:
                    self.message='Result discarded'
                    self.b.phase='idle'
        if self.restore_pending:
            self.restore()
            return True
        if self.saved is None: return False
        if st.get('steam_ui'):
            self.abort('Steam menu opened');return True
        if not st.get('fresh'):
            # Transient compositor status gaps are not a cancellation.
            if now >= self.b.deadline:
                self.b._finish(self.b.candidate, False, 'Compositor telemetry unavailable within 15 seconds')
                self.restore()
            return True
        if ctx!=self.b.context:
            self.abort('Game, display or power source changed');return True
        act=self.s.governor.actuator
        owned=act.verify_ownership()
        if not owned.get('owned'):
            self.abort('External power change');return True
        temp = sensors.get('temp_c')
        if isinstance(temp, (int, float)) and temp>=85:
            self.abort('Thermal protection');return True
        want = self.saved if self.validating else Policy(0,0,ctx['post'],self.s.hud_path,0,self.saved.hdr)
        self.s.coord.want(want)
        self.s.coord.tick(st)
        if not self.s.coord.engine_runs(want,st):
            if now >= self.b.deadline:
                self.b._finish(self.b.candidate, False, 'Compositor did not confirm native measurement mode within 15 seconds')
                self.restore()
            return True
        if self.validating:
            if now >= self.b.deadline:
                self.b.result['passed']=False
                self.b.result['reason']='Display verification exceeded the 15-second budget'
                self.restore(); return True
            if self.display_start is None:
                self.display_start = {k: st.get(k) for k in ('real','gen','repeat','focus_frames')}
            if st.get('time_ns') != self.fg_last_seq:
                self.fg_last_seq=st.get('time_ns')
                frames=st.get('native_frame_ms',[])
                if frames:
                    self.validation.append(dict(frame_ms=frames,draw_w=owned.get('draw_w') or 0,
                                                gpu=sensors.get('gpu_busy_pct') or 0,cpu=sensors.get('cpu_top_core_pct') or 0,temp=sensors.get('temp_c')))
            if len(self.validation)>=2:
                measured=summarize(self.validation, min_samples=2, min_frames=12)
                target=min(self.b.target, self.saved.base_fps or (refresh/max(1,self.saved.multiplier) if self.saved.multiplier>1 else self.b.target))
                passed=measured['low_fps']>=target*.9
                display = self.display_evidence(st, ctx)
                passed = passed and display['passed']
                self.b.result['display_verification'] = display
                self.b.result['fg_verified']=passed
                self.b.result['fg_measurement']=measured
                self.b.result['passed']=bool(self.b.result['passed'] and passed)
                self.restore()
            return True
        sample=dict(seq=st.get('time_ns'),frame_ms=st.get('native_frame_ms',[]),
                    draw_w=owned.get('draw_w'),tdp=owned.get('observed_tdp_w'),
                    gpu=sensors.get('gpu_busy_pct'),cpu=sensors.get('cpu_top_core_pct'),
                    temp=sensors.get('temp_c'),fresh=st.get('fresh'),menu=st.get('steam_ui'))
        watts=self.b.feed(sample,context=ctx,now=now)
        if watts is not None:
            if not act.set_tdp_w(watts).get('success'): self.abort('TDP readback failed')
        if self.b.phase=='aborted': self.restore()
        elif self.b.phase=='result':
            if not self.b.result or not self.b.result.get('passed'):
                self.restore()
            else:
                self.validating=True
                self.validation=[]
                self.display_start=None
                self.fg_last_seq=None
        return True

    def display_evidence(self, st, ctx):
        """Policy acknowledgement is not evidence of actual frame display."""
        start = self.display_start or {}
        delta = {}
        for key in ('real', 'gen', 'repeat', 'focus_frames'):
            a, b = start.get(key), st.get(key)
            delta[key] = b-a if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b >= a else None
        generated_required = bool(self.saved and self.saved.multiplier)
        passed = (delta['real'] or 0) > 0
        if generated_required:
            passed = passed and (delta['gen'] or 0) > 0
        if 'detail=' in ctx['post'] and ctx.get('hdr') == 'sdr':
            passed = passed and st.get('focus_status') == 'processing' and (delta['focus_frames'] or 0) > 0
        return dict(passed=bool(passed), generated_required=generated_required, counters=delta)

    def status(self):
        act=self.s.governor.actuator.status() if self.saved else {}
        return dict(self.b.status(),message=self.message,validating=self.validating,restore_pending=self.restore_pending,draw_w=act.get('draw_w'))
