# Control-loop churn: sandbox replay of Deck telemetry (after 3.3.2)

Method label: **sandbox replay of Deck telemetry**. These are model results on recorded scene
load, not a Deck measurement. Nothing here has been run on a Deck yet.

## Question

Deck telemetry from GFG 3.2.0–3.3.0 shows a busy control loop during play. The Deck's own
activity log (12.9 h of play from 3.2.0 on) has 98 TDP writes/h, 32 policy sends/h, 36 pilot
moves/h, 29 CPU-cap changes/h and 28 Power Split changes/h. Every policy change shifts the frame
cadence (a visible jerk), and TDP writes line up with pace dips. 3.3.1 added the per-point retry
back-off and "Governor calm". Is that enough, and what else can be cut without making real frames,
time short of the point or energy worse?

## Method

`sandbox/replay.py` (new) reads the report folders' `samples.jsonl*` as data, de-duplicates them
by time and cuts them into sessions (one game, one refresh rate, gaps up to 15 s filled, sessions
under 2 min left out): 68 sessions, 21.1 h of game time, 3.0–3.3.0, mostly Autopilot (15.7 h).

For each second it inverts the virtual Deck's own model (`sandbox/vdeck.py`) to get the scene
load independent of what the controllers did at the time:

- GPU frames at 15 W = (100 · real / GPU busy) / ((TDP − 2.5) / 12.5)^0.55, / 0.92 while generating
- CPU frames = 95 · real / busiest core %, / CPU clock share when capped

That scene then plays again on the virtual Deck under the code being tested: one `Service` for
the whole replay (the game book and TDP model learn across sessions as on the Deck), each session
with the recorded refresh rate, player TDP, objective changes, charger (SteamOS re-applies its
TDP on each change) and battery. The room temperature per session is fitted so the model's APU
temperature matches the recorded one at the recorded draw. Power Split and the GPU clock ceiling
are off, as by default since 3.3.0.

Calibration (3.3.2 replay vs what the Deck recorded on the same seconds): real fps 33.9 vs 33.6,
APU draw 11.77 W vs 11.85 W, share of locked seconds under 93 % of the point 13.4 % vs 16.4 %;
on the Deck about a third of the Governor's steps down were taken back, in the replay 32 %.

Counted per hour of game time: TDP writes, policy changes (multiplier / base FPS / Auto floor the
engine is told), locked-point changes, trials, CPU-cap changes; "short" = seconds under 93 % of
the point (Autopilot's tolerated dip), "deep" = under 80/90 of it; real fps; the model's APU draw
(energy proxy). "Steady" = seconds inside 5-min stretches whose scene load varies by at most 15 %
(6.6 h). The replay is deterministic; to tell a change from chance each configuration also ran
5 times with ±2 % per-second scene noise (seeds 1–5). The table gives mean ± SD of those 5 runs.

    python3 -m sandbox.replay <report>/gfg [<report>/gfg ...] [--noise 0.02 --seed N] [--split]

## Result

| all 21.1 h (5 runs, mean ± SD) | 3.3.2 | this branch | change |
|---|---|---|---|
| TDP writes / h | 65.6 ± 1.4 | 62.1 ± 1.2 | −5 % |
| policy changes / h | 28.7 ± 0.7 | 24.3 ± 0.2 | −15 % |
| point changes / h | 20.7 ± 0.4 | 16.7 ± 0.2 | −19 % |
| trials / h | 13.4 ± 0.4 | 11.6 ± 0.2 | −14 % |
| CPU-cap changes / h | 0 | 0 | (Power Split off) |
| short of the point, % of locked s | 13.50 ± 0.24 | 13.40 ± 0.26 | same |
| deep (under 80/90), % | 8.99 ± 0.08 | 8.97 ± 0.11 | same |
| real fps | 33.97 ± 0.04 | 34.05 ± 0.03 | +0.2 % |
| APU draw, W (energy proxy) | 11.78 ± 0.02 | 11.77 ± 0.02 | same |

| steady 6.6 h | 3.3.2 | this branch |
|---|---|---|
| TDP writes / h | 44.8 ± 3.9 | 41.5 ± 2.7 |
| policy changes / h | 20.5 ± 1.5 | 17.8 ± 0.6 |
| point changes / h | 12.7 ± 0.7 | 10.6 ± 0.7 |
| short, % | 9.04 ± 0.39 | 8.96 ± 0.51 |
| deep, % | 3.90 ± 0.15 | 3.94 ± 0.12 |
| real fps | 34.36 ± 0.11 | 34.20 ± 0.05 (−0.16, about 1.5 SD: the one number to watch) |
| APU draw, W | 12.72 ± 0.04 | 12.67 ± 0.03 |

Deterministic replay (no added noise): policy changes 26.9 → 24.9 /h, point changes 19.5 →
17.5 /h, TDP writes 63.4 → 63.8 /h, real fps 33.87 → 34.14, draw 11.77 → 11.80 W, short 13.4 →
13.6 %. One run is one draw of a chaotic loop; the 5-run means above are the result.

Per game (8 noisy runs each): 582160 (7.9 h) policy changes −17 %, draw −0.10 W, real −0.16 fps;
668580 (5.5 h) −11 %, the rest the same; 1313140 (2.2 h) −29 %, real +1.2 fps at +0.3 W;
**1716740 Starfield (0.9 h) worse: policy changes +16 %, short 31.5 → 33.0 %** (the game cannot
hold x3 there, see below; the sample is under an hour and its point changes vary ±4/h run to run).

The existing scenarios: all 41 `sandbox.run` scenarios pass; `sandbox.stress --seeds 30` 38/39 as
on 3.3.2 (`autopilot_heavy` at 34 fps fails on main as well, unchanged); 189 unit tests pass.

**The targets (≤ 20 TDP writes/h, ≤ 8 point changes/h in steady scenes) are not met.** Steady play
is at 41.5 writes/h and 10.6 point changes/h. What would get closer costs real frames or energy in
this model; see "left out".

## What changed (Autopilot only; Balanced, Quality and Battery keep 3.3.2's rules)

1. **Headroom must last.** The early climb on GPU headroom needs headroom in guard windows for
   10 s in a row, not in one window.
2. **No climb straight back into a point the game fell from.** After a fall at full power the
   point waits 30 s, doubling with each fall in this game (up to 16 min), whatever path would climb
   sooner (headroom, benchmark, the regular wait). 3.3.1's back-off covered failed trials only.
3. **Median pace.** A guard window judges the median pace, as Autopilot already judged the median
   frames: one hitch second (a loading stall) is not a game that got heavier.

## Tried and left out

Each measured as above (3–5 noisy runs), on top of 3.3.2 or of the branch:

| change | effect | why left out |
|---|---|---|
| minimum 120–300 s between TDP steps down once a level failed at this point (or always) | writes −15…−33 %, short up to −1.7 pts | real −0.1…−0.6 fps and draw +0.04…+0.10 W, beyond noise: fewer steps down leave the TDP above need longer |
| no probe down for 45 s after a point change | writes −28 % | real −0.19 fps, draw +0.05 W |
| headroom sustained 20–60 s, fall back-off 60–120 s | policy changes −31…−36 % | real −0.1…−0.7 fps (less time at higher points; draw falls with it), short up to +0.5 pts |
| point falls only after two short guard windows (unless under 80/90) | real +0.2…+0.36 fps, policy −12 % | short +0.2…+0.4 pts and deep +0.2 pts, beyond noise |
| straight back to the pre-trial TDP after a failed trial | no measurable change | no benefit shown |
| a point revisited this session starts at its lowest held TDP | no measurable change | no benefit shown |
| longer Governor calm (60–120 s) / floor back-off (10 min) / stable unlock | writes −5…−20 % | real −0.3…−0.6 fps or energy worse beyond noise |

The pattern: in this model every second the TDP sits above what the scene needs costs draw, and
every minute spent at a lower point costs real frames. Fewer probes and fewer climbs therefore
trade against energy and real fps; only the three changes above cut churn without that cost.

**Power Split / CPU cap.** Already off by default since 3.3.0 (0 CPU-cap changes/h). The replay
with it on (`--split`): 37 CPU-cap changes/h, real +0.1 fps, draw −0.03 W, short −0.4 pts in this
model, whose CPU/GPU budget sharing is an assumption (vdeck's `CPU_BOOST_W`). The earlier Deck
finding (each cap change raised the 8 s pace < 0.98 share from 2.6 to 4.0 %) is a measurement and
outweighs it: it stays off.

## Deck note: Starfield on 3.3.2 (from the user's run today)

Autopilot locked cap 30 (x3) while the game rendered 24.8–28.9 fps at 15 W, so x3 does not hold
there; x3.75 stays locked by default since 3.1.1 ("above x3 plays very badly"), and the pilot
reports that the lowest allowed point does not hold. In the fixed x2 mode (cap 45) the game made
26 fps and the engine filled the 90 Hz output, i.e. an effective x3-and-more cadence with
repeated frames although the label says x2. The replay agrees: Starfield spends 85 % at 30 and
about a third of the time short of it under any variant tried. Nothing about this is changed
here: what the label should say and whether a game that cannot hold x3 should get x3.75 are UI
and user decisions that need a mockup first.

## Risks

- A replay, not a Deck run: the fps-against-watts curve, the draw (including the "boost uses the
  headroom" term) and the CPU/GPU split are vdeck's model; frame-time noise within a second is not
  in a 1 s sample; pace in the replay comes from the model's repeat counter, not the Deck's.
- Climbs after a fall wait up to 16 min when the same point keeps falling in one game: a scene
  that gets lighter for good regains its x2-family point later than on 3.3.2.
- Starfield-like games (cannot hold x3) showed more churn in the replay with this branch.
- Needs a Deck check before any release: TDP writes/h, policy sends/h, pace dips and real fps
  from the activity log and samples, against these numbers.
