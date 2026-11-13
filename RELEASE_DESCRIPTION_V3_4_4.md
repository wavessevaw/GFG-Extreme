# GFG Extreme 3.4.4 — Official Release

## About GFG Extreme

GFG Extreme is a free, open-source project designed to make gaming on Steam Deck more comfortable. It combines game-aware performance and power management with independent frame generation, aiming to reduce manual setup and make better use of the hardware players already own.

The project has benefited from earlier open-source work and community research. It has since developed its own components and direction, including **GSF Kedavra**, an independent frame-generation engine integrated into Gamescope.

- **October 6, 2026:** GFG Extreme introduced automatic, adaptive TDP management.
- **October 21, 2026:** GSF Kedavra was publicly introduced as an independent frame-generation engine.

We appreciate the contributions of other developers in this space. Open development, shared research and clear attribution benefit the whole community.

### Looking Ahead: GFG Extreme 5.0

We are exploring possibilities for a future generation of GFG Extreme, particularly in the area of visual smoothness and efficiency on Steam Deck.

That research may involve improving existing frame-generation methods, reconsidering parts of the current pipeline or investigating fundamentally different approaches to the gaming experience. **It is a research direction, not a finished technology or a promised release date.**

Our focus is on improvements players can actually feel: more consistent motion, fewer visual artifacts, responsive controls and sensible use of power.


---

## GTA VI. 90 FPS. Steam Deck OLED.

Some consider it impossible.

We consider it a technical objective.

**GTA VI on Steam Deck is a console Remote Play scenario, not a native Steam Deck port.** The game runs on a **PlayStation 5** or **Xbox Series X|S**, while its video is streamed to Steam Deck in SteamOS Gaming Mode through applications such as:

- **Xbox Series X|S:** [Greenlight](https://github.com/unknownskl/greenlight) — Xbox Remote Play.
- **PlayStation 5:** [chiaki-ng (Chiaki4deck)](https://github.com/chiaki-ng/chiaki-ng) — PlayStation Remote Play.

With our independent GSF Kedavra engine running in Gamescope, the target is to turn a stable 30 FPS streamed source into **up to 90 output FPS** on Steam Deck OLED through ×3 frame generation.

**30 streamed source FPS × 3 = up to 90 displayed FPS.**

The game still renders on the console. Actual results depend on the streaming client, source frame cadence, decoding and network conditions; GTA VI-specific performance has not yet been verified.

No third-party frame-generation engine required.

---

## What's New in 3.4.4

- **Benchmark Apply** — Apply the measured TDP and native-FPS point directly to the active game.
- **Governor Fix** — The selected TDP is no longer immediately overwritten. Adaptive control remains active.
- **HUD Controls** — APPLY / DISCARD and RETRY / DISCARD actions.
- **Independent Profiles** — Separate Benchmark results for Quality, Balanced, Battery and Autopilot.
- **GSF Kedavra 1.6.2** — Independent frame-generation engine. Reconstruction algorithms remain unchanged.

---

## How to Run the In-Game Benchmark

1. **Launch a game** in SteamOS Gaming Mode and make sure the GFG Extreme HUD is visible.
2. **Touch and hold the HUD on the screen for at least 0.8 seconds.** The Benchmark starts directly in the running game; there is no need to open the Decky menu.
3. **Let the measurement finish** (up to 15 seconds). Stay in a stable gameplay scene without touching the Benchmark panel or opening the Steam menu. GFG measures native FPS and TDP and displays the recommended point.
4. **Tap APPLY** on the left side of the result panel to accept the measured point for the current game and selected performance mode. The Governor starts from that TDP and continues adapting when necessary.

Tap **DISCARD** on the right to ignore the result. If the Benchmark cannot find a valid point, tap **RETRY** to measure again.

---

## One Plugin. More Time to Play.

You bought a Steam Deck to enjoy games, not to spend every session juggling tools, power limits and performance settings.

**That's who GFG Extreme is built for: the player.** It identifies the running game, works with game-specific settings and adapts performance and power management to the situation. When more performance is needed, it can respond. When it isn't, it aims to reduce unnecessary power use and help your battery last longer.

For suitable games, **30 native FPS ×3 can produce 90 output FPS** through frame generation. These are not 90 native game updates, and results depend on the game and workload. That's why we keep refining frame pacing, visual reconstruction, artifacts and power efficiency together. The number on the counter matters less than how the game actually feels.

**Our goal is to make GFG Extreme useful with as little setup as possible.** Less tweaking. More time playing.

Development is guided by the practical experience of players, game testing and feedback from the community.

If GFG Extreme improves your experience, please **star the repository**, share the project and tell us what works and what needs improving. Every report and every bit of support helps us keep building for players.

[**Support GFG Extreme on GitHub**](https://github.com/wavessevaw/GFG-Extreme) · [Feedback & Issues](https://github.com/wavessevaw/GFG-Extreme/issues)

---

Optional support: [Tribute](https://web.tribute.tg/d/RSU)

---

## What's Next

Version 3.4.4 is available now. We will keep refining the current experience and exploring longer-term ideas at a measured pace.

Thanks to everyone who tries the project, reports issues and supports independent development.

**GFG Extreme. Built by a player. For players.**
