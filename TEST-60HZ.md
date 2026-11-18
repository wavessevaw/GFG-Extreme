# GFG Extreme 3.4.4-response.1

Experimental scheduler build from GFG 3.4.4 and Kedavra 1.6.2. Install the inner Decky ZIP, use Setup → Reinstall to deploy its Gamescope, then reboot. Verify installed/runtime version includes kedavra-a6f1c6d. For rollback reinstall the stock v3.4.4 Decky ZIP, reinstall its engine in Setup and reboot.

Set the actual display to a fixed 60 Hz (59.94 Hz is supported), choose fixed ×2 and turn camera Boost off for the comparison. Use the same game, controller, display, scene, graphics settings and power limit on both builds. A 60 FPS cap on a 90 Hz output does not activate this path. Fixed ×3 is a control. Automatic selection and Battery policy follow the stable baseline. This branch is independent of the Resource Manager candidates.

After a generated output, if the next planned output would interpolate the same pair again, the scheduler may display the pair's real endpoint up to one refresh early. It checks the following content position against available analysis. This is not unconditional newest-frame presentation. The path requires a 30 FPS source cap, ×2, fixed approximately 60 Hz and disabled adaptive sync during generation.

For A/B, record at least three matched runs on each build with 30 native FPS and a scene dipping below 30. Track native frametime, repeated frames and pan judder. For input-to-screen latency, film the physical input and first visible response together at high frame rate. Separate LCD/OLED/TV results. On a TV keep Game Mode and its interpolation setting identical.

Five simulator seeds per profile, 60 seconds with the first 5 seconds excluded. At 29/35 ms model game time (typical/P99), mean content age went from 50.18 to 38.30 ms, P95 stayed at 50 ms, and repeats increased from 17 to 29 across the five runs. At 36/49 ms, P95 fell from 66.7 to 50 ms and repeats increased from 22 to 48. At 20/26 ms mean age was effectively unchanged. Content age is a scheduler-model metric. Physical input latency and visual acceptability on Deck remain unverified.
