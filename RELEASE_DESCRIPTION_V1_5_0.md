## GFG Extreme 1.5.0: Smart power split

The Steam Deck's CPU and GPU share one power limit. In most demanding games the GPU sets the frame rate while the CPU waits, yet the CPU still boosts to full clock between frames and spends watts the GPU could use. 1.5 gives those watts to the GPU, automatically.

### How it works
- In a GPU-bound game (or one at the Governor's power cap), GFG lowers the CPU's top clock **one step at a time**: 3.5 → 3.0 → 2.4 → 2.1 → 1.8 GHz. It never goes below 1.6 GHz and never above your own limit.
- A step happens only when the busiest CPU core still has room at the lower clock, and each step is a 10-second trial.
- The GPU gets the freed watts. The Governor's own search turns them into **a lower TDP for the same real frames**.

### Real frames first
- If real frames fall short or a CPU core nears its limit, the cap comes off **immediately**.
- Loading screens, Steam's menu, Frame OS Act and any mode change run at full CPU clock.

### Measured in your game
- Now and then GFG lifts the cap for a few seconds and compares **GPU clock per watt** with and without it. **Details → CPU / GPU power split** shows the result.
- The deepest step that held is remembered per game. A game where the split makes no measurable difference gets it switched off automatically, and it is re-checked every 8 sessions.
- Recorded logs show the clock steps, why the cap came off, and the A/B result with its confidence interval.

### Always given back
- Your CPU limit comes back when the game ends, when you press Stop and when the plugin unloads, even after a crash.
- If another tool (PowerTools, a script) sets the CPU clock, GFG leaves it alone.
- To turn the feature off, use **Details → Smart power split**.

### Install
Download `GFG-Extreme-v1_5_0.zip` below and install it with Decky Loader (*Install from zip*) over your current version. Settings, profiles and everything GFG learned are kept.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
