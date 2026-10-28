"""Honest multipliers (user, 2026-10-28): xN means exactly N-1 generated frames between two real
frames, so the screen gets N x base new frames per second. The panel's refresh is never changed
(user, 22:22: the OLED always runs 90 Hz; the LCD and a dock's TV keep theirs): an output under
the refresh is shown with repeated refreshes (an uneven hold, "judder"). x3 is the most in every
mode (user, 22:21: no more than two intermediates); the Setup toggle's x3.75 / x4 is not chosen.

A point of generation "Auto" is a pair (base, N): the engine runs xN with the cap refresh / N
(x2 at 45, x3 at 30 on 90 Hz) and the base is the game's rate the pilot and the Governor aim at
under that cap (x2 at 40: the Governor holds the game near 40, 80 on screen). Clean cadences
divide the refresh (at 90 Hz x2@45 and x3@30, at 60 Hz x2@30 and x3@20). A game short of its cap
gets N x its fps on screen, the holes filled by repeating the last frame. Per objective (user, 22:17: the 90 target is
Autopilot's only):

  autopilot  x2 aiming at the game's sustainable rate, 32-45 (64-90 on screen); x3 aiming at
             27-30 only for a game that cannot hold about 32.
  balanced   x2 aiming at 45, 40 or 35 (uneven 70 / 80 on screen) while the game holds it,
             else x3 at 30: x3 only for a game that cannot hold more than about 30.
  quality    x2 at 45 only; never x3.
  battery    x3 at 30.
  light games (the game list) stay at x2; a dock's TV gets refresh / N with integer N only.

Fixed x2 / x3 keep the cap refresh / N and Custom keeps its base (a fractional multiplier
alternates one and two intermediates, never three): those requests do not change.

The pilot's measure, lock, guard, trials and back-offs work on the bases as before. Nothing here
runs until the engine reports that it draws strict multipliers (status "strict_multiplier").
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

BAND = 80.0 / 90.0   # Autopilot's tolerated output dip
MIN_BASE = 20
MAX_N = 3
X2_FLOOR = 32   # Autopilot: the lowest x2 aim on 90 Hz (scaled to the refresh)

Ladder = List[Tuple[int, int]]   # (base, N), ascending base


def cap(n: int, refresh: int) -> int:
    """The engine's cap for xN: always refresh / N (x2 at 45, x3 at 30 on 90 Hz)."""
    return int(refresh) // int(n)


def n_for(pairs: Ladder, base: int) -> int:
    """N for a point: its ladder entry, else the nearest entry below it, else the lowest one (a
    point under the ladder, from a back-off or a known game, keeps the bottom's N: x3 at 25 shows
    75, x2 only 50)."""
    best = None
    for b, n in sorted(pairs):
        if b <= base or best is None:
            best = n
    return best or 2


def clean(base: int, n: int, refresh: int) -> bool:
    """The output divides the refresh: every frame is held the same number of refreshes."""
    out = base * n
    return out > 0 and refresh % out == 0


def _span(lo: int, hi: int) -> List[int]:
    """The ends and the middle of lo..hi (few steps: few point changes)."""
    if hi < lo:
        return []
    return sorted({lo, (lo + hi) // 2, hi}) if hi - lo >= 4 else sorted({lo, hi})


def _sorted(pairs: Ladder) -> Ladder:
    best: Dict[int, int] = {}
    for b, n in pairs:
        if b >= MIN_BASE and 2 <= n <= MAX_N:
            best[b] = min(n, best.get(b, n))
    return sorted(best.items())


def ladder(objective: str, refresh: int, dock: bool = False, light: bool = False) -> Ladder:
    """Generation "Auto" as honest pairs. The cap is refresh / N (x2 at 45, x3 at 30 on 90 Hz) in
    every objective but Autopilot, which alone aims at 90 on screen and also uses the bases inside
    its tolerated dip (x2 at 40-44, x3 at 27-29 on 90 Hz; not on a dock's TV)."""
    hz = int(refresh or 90)
    x2_only = objective == "quality" or light
    if objective == "autopilot" and not dock and not light:
        # Native frames first (coordinator, 2026-10-28): a game that sustains about 32 or more
        # gets x2 aiming at its own rate (64-90 on screen, the accepted honest dip); x3 only below.
        band = math.ceil(BAND * hz)
        x2 = sorted({X2_FLOOR * hz // 90, 35 * hz // 90} | set(_span(math.ceil(band / 2), hz // 2)))
        return _sorted([(b, 2) for b in x2]
                       + [(b, 3) for b in _span(math.ceil(band / 3), hz // 3)])
    out = [(hz // n, n) for n in range(2, MAX_N + 1) if not dock or hz % n == 0]
    if objective == "balanced":
        # Native frames first: x3 only for a game that cannot hold more than about refresh / 3.
        out += [(b, 2) for b in range((hz // 3 // 5 + 1) * 5, hz // 2, 5)]
    if x2_only:
        out = [p for p in out if p[1] == 2] or out[:1]
    elif objective == "battery":
        out = [p for p in out if p[1] == MAX_N] or out[-1:]
    return _sorted(out)
