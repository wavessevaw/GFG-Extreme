# Honest multipliers: sandbox replay of Deck telemetry (policy only)

Method label: **sandbox replay of Deck telemetry**. These are model results. Scene loads come
from the recorded sessions (21.1 h of game time in the reports' `samples.jsonl`, read as data).
They were played through the real service against the virtual Deck in `sandbox/vdeck.py`. No
Deck ran this code, and the engine side (strict xN) is modelled.

## Rules implemented (user, 2026-10-28)

- **What xN means.** xN is exactly N-1 generated frames between two real frames, so N x base
  new frames reach the screen.
- **x3 is the most.** This holds in every mode. No policy chooses x3.75 or x4
  (`pilot.ABOVE_X3_POLICY = False`), and the Setup toggle and the UI are untouched.
- **The refresh is never changed.**
  - The OLED stays at 90 Hz. An LCD or a dock's TV keeps its own refresh.
  - The refresh-switch stub is gone.
  - When the output is under the refresh, the remaining refreshes repeat a frame (an uneven
    hold).
- **The engine cap is always refresh / N.** That is x2 at 45 and x3 at 30 on 90 Hz, and x2 at 30
  and x3 at 20 on 60 Hz.
  - In generation "Auto", a point is a pair (aim, N). The pilot and the Governor aim at the game
    rate under that cap. For example, x2 aiming at 40 means the Governor holds the game near 40,
    with 80 frames on screen.
  - Pace for control (`Service._control_pace`) does not count the repeats this aim plans for.
  - The HUD keeps the plain pace.
- **Fixed x2 / x3 and Custom requests do not change.**
- **The ladder of each objective** is in `honest.ladder`:

| Objective | 90 Hz points (aim, N) | Why |
|---|---|---|
| Autopilot | x2 at 40, 42, 45; x3 at 27, 30 | The only mode that aims at 90 on screen, with dips to 80 tolerated |
| Balanced | x2 at 35, 40, 45; x3 at 30 | Native frames first: x3 only when the game cannot hold more than about 30 |
| Quality | x2 at 45 only | Never x3 |
| Battery | x3 at 30 | |
| Light game (list) | x2 only | |
| Dock TV | refresh / N with integer N only (60 Hz: x2 at 30, x3 at 20; Balanced also x2 at 25) | |

A point under the ladder (from a back-off or a known game) keeps the bottom entry's N
(`honest.n_for`). For example, x3 aiming at 25 shows 75 frames, where x2 would show only 50.

None of this runs until the engine reports `strict_multiplier: true` in its status. Until then,
3.3.2's requests (fill to the refresh) stand unchanged. This is checked by
`tests/test_sandbox.py::HonestTest`.

## Replay: per mode, light / medium / heavy games

- **Runs.** Each objective was forced on every session.
  - Noise was ±2 %, with 3 seeds per arm.
  - The cost of generation was modelled as `gen_cost` 0.08: a generated frame at 60/s costs the
    game 8 % of its rate.
- **Classes** come from each session's median load at 15 W: light at 50 fps and above, medium at
  35-50 fps, heavy under 35 fps.
- **3.3.2** is the code of `ddc7352`, fill mode, with the same virtual Deck and replay.
- **Honest** is this branch with the engine's strict xN.
- **Column meanings.**
  - "short" is the time the game ran under 95 % of its aim.
  - "even" is the time with every frame held the same number of refreshes.
  - "out" is the new frames on screen per second.
- **Refresh** is fixed in every row: 90 Hz on the handheld; the docked sessions keep their TV's
  60 Hz. The x2@30 and x3@20 shares are those docked sessions.
- The run-to-run spread on real fps is at most ±0.5, and mostly ±0.1.

### Autopilot

| Class | Arm | Main points | Real fps | W | Short % | Out fps | Even % |
|---|---|---|---|---|---|---|---|
| light | 3.3.2 | fill@45 64 %, @40 15 % | 40.42 | 9.92 | 9.7 | 87.8 | 57 |
| light | honest | x2@45 57 %, x2@42 14 %, x2@40 12 % | 41.15 | 9.97 | 9.5 | 87.3 | 47 |
| medium | 3.3.2 | fill@35 39 %, @30 38 % | 34.10 | 12.01 | 8.7 | 87.8 | 37 |
| medium | honest | x3@30 38 %, x3@27 32 %, x2@40 15 % | 33.15 | 11.29 | 7.9 | 86.4 | 35 |
| heavy | 3.3.2 | fill@30 82 % | 27.56 | 13.04 | 21.4 | 78.2 | 53 |
| heavy | honest | x3@27 65 %, x3@30 14 % | 26.99 | 12.66 | 14.8 | 77.4 | 19 |
| **all** | 3.3.2 | | **33.94** | **11.79** | 12.0 | 85.5 | 45 |
| **all** | honest | | **33.48** | **11.33** | 9.9 | 84.4 | 34 |

### Balanced

| Class | Arm | Main points | Real fps | W | Short % | Out fps | Even % |
|---|---|---|---|---|---|---|---|
| light | 3.3.2 | fill@45 49 %, @30 19 %, @40 18 % | 39.26 | 9.97 | 4.3 | 88.8 | 58 |
| light | honest | x2@45 49 %, x2@40 18 %, x3@30 16 % | 41.54 | 10.37 | 4.0 | 87.9 | 58 |
| medium | 3.3.2 | fill@30 52 %, @35 27 % | 33.48 | 11.88 | 5.5 | 88.5 | 49 |
| medium | honest | x3@30 43 %, x2@35 35 %, x2@40 16 % | 36.20 | 12.43 | 5.2 | 84.4 | 41 |
| heavy | 3.3.2 | fill@30 79 % | 27.14 | 12.95 | 18.9 | 78.6 | 57 |
| heavy | honest | x3@30 77 %, x2@25 (TV) 13 % | 27.87 | 13.14 | 18.5 | 77.7 | 53 |
| **all** | 3.3.2 | | **33.25** | **11.70** | 8.5 | 86.1 | 53 |
| **all** | honest | | **35.39** | **12.13** | 8.2 | 83.6 | 48 |

### Quality

| Class | Arm | Main points | Real fps | W | Short % | Out fps | Even % |
|---|---|---|---|---|---|---|---|
| light | 3.3.2 | fill@40 74 %, @45 26 % | 40.61 | 10.82 | 5.2 | 88.6 | 24 |
| light | honest | x2@45 100 % | 43.76 | 11.34 | 9.5 | 87.8 | 86 |
| medium | 3.3.2 | fill@40 93 % | 37.83 | 13.26 | 30.7 | 84.4 | 6 |
| medium | honest | x2@45 100 % | 39.67 | 13.58 | 54.8 | 79.6 | 33 |
| heavy | 3.3.2 | fill@40 79 %, @25 19 % | 29.81 | 13.62 | 67.0 | 67.8 | 2 |
| heavy | honest | x2@45 81 %, x2@30 (TV) 19 % | 31.04 | 13.88 | 75.2 | 62.5 | 20 |
| **all** | 3.3.2 | | **36.51** | **12.79** | 33.7 | 81.3 | 9 |
| **all** | honest | | **38.50** | **13.14** | 49.4 | 77.3 | 42 |

Quality's "short" rises because the aim is now 45 where 3.3.2 aimed at 40. The game is given
the frames it can make. The higher number is not a drop in frames.

### Battery

The arms are equal to within 0.01 fps and 0.01 W.

| Class | Arm | Points | Real fps | W | Short % | Out fps |
|---|---|---|---|---|---|---|
| light | 3.3.2 / honest | x3@30 100 % | 29.60 / 29.61 | 7.46 / 7.47 | 4.1 / 4.0 | 88.8 |
| medium | 3.3.2 / honest | x3@30 100 % | 29.41 / 29.41 | 10.20 / 10.20 | 6.7 / 6.7 | 88.2 |
| heavy | 3.3.2 / honest | x3@30 81 %, x3@20 (TV) 19 % | 26.11 / 26.13 | 12.36 / 12.38 | 20.8 / 20.3 | 78.3 / 78.4 |

## What got better, what got worse

- **Autopilot.**
  - Better: 0.46 W less (−3.9 %) and less time short (12.0 → 9.9 %).
  - Worse: 0.46 fewer real fps overall (−1.4 %), and 0.95 fewer on medium games.
  - Why: a game that holds 31-39 gets x3 aiming at 27-30 (81-90 on screen). 3.3.2 gave it fill
    at 35 (90 on screen with filled frames). Honest x2 there would show only 70-78, under
    Autopilot's tolerated dip.
  - Even cadence is lower (45 → 34 %), because x2 at 40-42 and x3 at 27 are uneven holds by
    design.
- **Balanced.**
  - Better: 2.14 more real fps (+6.4 %), and +2.7 on medium games, because x3 is kept for games
    that cannot hold more than about 30.
  - Worse: 0.43 W more (+3.7 %) and 2.5 fewer frames on screen.
- **Quality.**
  - Better: 1.99 more real fps (+5.4 %), and even cadence rises from 9 to 42 %.
  - Worse: 0.35 W more (+2.7 %) and 4 fewer frames on screen.
- **Battery.** Unchanged.

## Assumptions and risks

- **The engine side is assumed.** The convention is: `strict_multiplier: true` in the status,
  `kfg_multiplier` N >= 2 with `kfg_base_fps` refresh / N, and repeated frames when the game is
  short. The engine must implement exactly this. Until it does, the plugin behaves like 3.3.2.
- **The cost of generation is a model.** `gen_cost` 0.08 per 60 generated frames per second is a
  guess. A higher real cost would make x3 dearer, which would favour Balanced's x2.
- **Judder is counted, not felt.** "Even %" is a frame-hold count. Whether x2 aiming at 35-40
  (70-80 on screen) feels better than x3 at 30 (90, even) has to be judged on a Deck.
- **The labels are those of the docked sessions.** In the tables, x2@25, x2@30 and x3@20 come
  from docked sessions at 60 Hz. The labels do not show the refresh.
