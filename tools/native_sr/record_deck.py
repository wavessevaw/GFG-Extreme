"""Read-only Deck recorder. Keeps raw, per-status native frame intervals with display and power evidence."""
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"py_modules"))
from gfg_plugin.host_sensors import HostSensors


def percentile(values,p):
    sorted_values=sorted(values)
    return sorted_values[round((len(values)-1)*p)] if values else None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seconds",type=int,default=90)
    parser.add_argument("--app",type=int,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.seconds < 1 or args.seconds > 3600: parser.error("duration outside 1..3600 seconds")
    sensors=HostSensors()
    status=Path(os.environ.get("XDG_RUNTIME_DIR",f"/run/user/{os.getuid()}"))/"kedavra-status.json"
    power_paths=[p for p in Path("/sys/class/hwmon").glob("hwmon*/power1_average")
                 if (p.parent/"name").read_text().strip()=="amdgpu"]
    rows=[]; last_stamp=None
    with args.out.open("x") as f:
        deadline=time.monotonic()+args.seconds
        while time.monotonic()<deadline:
            try:
                st=json.loads(status.read_text())
                if (st.get("time_ns")!=last_stamp and time.time()-status.stat().st_mtime<3 and
                        st.get("app_id")==args.app and not st.get("steam_ui")):
                    last_stamp=st.get("time_ns")
                    try: apu_w=float(power_paths[0].read_text())/1e6 if power_paths else None
                    except (ValueError,OSError): apu_w=None
                    row=dict(wall_time=time.time(),status=st,sensors=sensors.sample(),apu_reported_w=apu_w)
                    rows.append(row)
                    f.write(json.dumps(row)+"\n");f.flush()
            except (FileNotFoundError,PermissionError,json.JSONDecodeError): pass
            time.sleep(.25)
    if not rows: raise SystemExit("No fresh, matching game status")
    durations=[v for row in rows for v in row["status"].get("native_frame_ms",[]) if v>0]
    slow=sorted(durations,reverse=True)[:max(1,round(len(durations)*.01))]
    print(json.dumps(dict(status_samples=len(rows),native_intervals=len(durations),
        native_fps=(1000/statistics.mean(durations)) if durations else None,
        native_1pct_low_fps=(1000/statistics.mean(slow)) if slow else None,
        native_p95_ms=percentile(durations,.95),native_p99_ms=percentile(durations,.99),
        managed_samples=sum(r["status"].get("sr_managed_app")==args.app for r in rows),
        sr_samples=sum(bool(r["status"].get("sr_selected")) for r in rows)),indent=2))

if __name__=="__main__":main()
