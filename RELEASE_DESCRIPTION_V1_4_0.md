## GFG Extreme 1.4.0: tell it how long you want to play

### Playtime target
"I want to play for three hours." Pick **2h, 3h, 4h or 5h** on Home, and GFG turns it into a power budget the game has to live within:

- It takes the energy left in the battery, divides it by the time you asked for, and subtracts what the screen, memory and fan draw — measured live as battery drain minus the APU's own draw. What remains is the APU's ceiling.
- The Governor plays **inside** that ceiling. When a scene gets heavier it keeps the picture smooth by generating a little more instead of spending watts the battery cannot afford. No TDP write can bypass it, emergency watts included.
- Home tells you where you stand: *holding 7.5 W so the battery lasts — 2h41 to go*, *no limit needed*, or — if even the Deck's lowest power cannot make it — how long the charge can actually last.
- In the game, the battery ring shows **GOAL 2h51** and stays green while the battery outlasts it, orange when it falls short.
- The ceiling is recalculated continuously but moves in small steps, so the TDP does not wander. The target survives a plugin restart, pauses on the charger and switches itself off once reached.

Works in Battery and Balanced mode.

### Also in 1.4
- Everything from 1.3.1: flicker-free in-game rings, Predictive Presentation in the Frame OS pacer, and the Frame OS fixes from the 1.3.0 review.
- READMEs (EN/RU) with a Playtime target section, fresh screenshots and a phone-friendly layout.

### Install
Download `GFG-Extreme-v1_4_0.zip` below and install it with Decky Loader (*Install from zip*) over your current version; settings, profiles and what GFG learned are kept.

The battery estimate drifts near the end of a charge, so GFG keeps 5 % in reserve; brightness or a game that changes its load later shifts the forecast.

### Verify your download
SHA-256 of the zip: `<sha256>` (see `SHA256SUMS.txt`).
