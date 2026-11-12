# GFG Extreme 3.2.1

Cleaner camera turns, steadier thin lines, smoother recovery after a game hitch, a simpler Dash
and a system profile for games. **Update engine** in Setup and reboot after installing.

## Picture
- **Fast camera turns.** The motion search also checks where each block's content comes from
  and where it goes, so walls, pillars and sky follow the camera as one surface.
- **Frame edges.** Blocks at the edge of the frame keep the motion of the image next to them on
  fast turns.
- **Thin straight lines.** Fences, wires, window frames and crosshair-like detail stay steady
  during slow pans.
- **Scene cuts.** A real cut shows the last real frame until the new scene arrives; fast turns
  and slow pans stay generated.
- **HUD.** HUD rows at the screen edges stay in place.

Engine test scenes (PSNR against the true frame, higher is better; line flicker, lower is better):

| Scene | 3.2.0 → 3.2.1 |
|---|---|
| Camera turn, 32 px per frame | 32.5 → 33.1 dB |
| Camera turn, 64 px per frame | 27.1 → 28.1 dB |
| Camera turn, 96 px per frame | 23.9 → 24.8 dB |
| Dark grainy turn | 35.3 → 35.7 dB |
| Fast pan | +2.0 … 2.6 dB |
| Thin lines, slow pan ×3 | 21.0 → 28.4 dB, flicker 34.8 → 12.7 |
| Thin lines, slow pan ×2 | 19.3 → 27.2 dB, flicker 38.6 → 14.1 |

## Frame delivery
- After a late game frame the engine catches up once and settles, without alternating faster and
  slower refreshes.
- The base FPS cap releases exactly one game frame per slot.

Scheduler simulator, tracking error P95:

| Case | 3.2.0 → 3.2.1 |
|---|---|
| Game hitch of 155 ms | 7.4 → 1.2 ms |
| Game hitch of 300 ms | 7.1 → 0.5 ms |
| ×3, game under its cap | 4.3 → 3.6 ms |
| ×3, game holding its cap | 1.0 → 0.6 ms |

Average latency changes by 0–3 ms; the extra analysis costs well under 0.1 ms per game frame.

## Dash
The Frame generation card has a single **Off** button. The mode (Autopilot, Battery, Balanced,
Quality) chooses the multiplier; tap Off to play a game without generation, tap it again to
bring generation back.

## System profile
Installed with the engine and removed with it: runtime kernel settings for memory (zram swap,
huge pages, earlier reclaim), the CPU scheduler and storage. Every value is saved first and
written back on **Remove**. **Setup → Save report to Desktop** shows how many were applied.
