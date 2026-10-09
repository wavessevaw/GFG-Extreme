# GFG Extreme 1.6.7

Official release of the ordinary GFG renderer. Restart running games after upgrading.

## Different goals, shared tools
- Battery keeps its autonomy-first power search. It can test a lower flow resolution only when adjacent control windows show at least 5% lower measured APU draw without a cadence regression.
- Balanced protects its existing real-frame floor and accepts a flow trial only for a useful draw or output-cadence improvement.
- Quality now preserves the player's render resolution in its automatic ladder. It can test a higher optical-flow resolution when there is GPU headroom, reverting if cadence or power cost fails the trial.
- Extreme retains its quarter-step ratios through 4x and inherited power ceiling. It can test a lower flow resolution for real/output cadence or GPU headroom. This is not a guarantee of more real frames.

## Confirmed flow-scale trials
A rare A/B/A trial compares one flow-scale step at the same point, target and power cap. Each resource change requires a fresh frame-generation acknowledgement from the same renderer context. There are settling windows, scene-drift checks and a rollback on missing acknowledgement, output starvation, menu entry, heat or context changes. TDP/CPU probing is paused during the comparison. Saved profiles are never edited, and point/power failure memory does not learn from temporary resource trials.

Settings includes **Automatic flow scale** with a disable switch. The tuner is experimental: image quality and physical Deck performance still need game-by-game validation. Frame OS Act and lighter/ultra performance profiles keep their saved flow settings; the tuner does not stack an A/B trial on top of those controls. Unknown renderer acknowledgement means no automatic tuning.

## HUD and CSS Loader theme
- The TDP ring is always green on external power, including a full battery or paused charging. On battery it changes smoothly from green at 65%, through yellow at 40%, to red at 15% or below. Its watts and fill are unchanged.
- ENERGY still shows saved TDP allowance in its centre and battery charge in its arc. Charger colour applies to TDP independently.
- **Settings → GFG theme → Install theme** copies the bundled theme into `~/homebrew/themes/GFG Extreme`. Install CSS Loader separately, reload its themes and enable GFG Extreme there. Updates preserve extra local files; failed directory replacement restores the previous theme, or keeps a recovery copy if rollback itself fails.

## Validation and limits
Backend policy, ACK, rollback, drift and cross-mode tests; native Frame OS/HUD integration and ordering; HUD pixel and cached-render benchmarks; frontend success/error cases; release archive validation.

Extreme, Frame OS Act and automatic flow tuning remain experimental features inside an official release. Unsupported boosters stay explicitly unavailable. GFG Open remains retired. No new generator or renderer model is introduced, and no measured on-device FPS/ghosting gain is claimed by this release.
