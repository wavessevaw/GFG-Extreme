# Resource Optimizer test candidate

Based on GFG Extreme 3.4.4. Install the full ZIP in Decky. The original bundled Gamescope runtime is unchanged. Open Power and check Resource Optimizer during a game. Reinstall the 3.4.4 ZIP to roll back.

Every five seconds during gameplay the backend samples CPU, memory and I/O PSI and a single KDE Baloo background service. Three successive observations must find CPU pressure of at least 5%, indexer activity of at least 0.25 core, and late native frame intervals. Only the designated desktop user's background.slice/kde-baloo.service with exclusively recognized Baloo processes and no descendant cgroups is eligible. Systems using other layouts remain in observation mode.

The desktop user manager runs a bounded 30-second trial at CPU weight 50. A private user-runtime receipt records the original default weight, boot ID and group inode. ExecStopPost restores the value after termination independently of Decky. The helper refuses nondefault weights and preserves external changes. A failed restoration leaves the receipt for the next trial. Reboot recreates runtime cgroups. A two-minute cooldown separates trials. CPU weight affects relative service among contending siblings and may have little effect across slices.

Memory and I/O pressure are observational. GPU activity attribution, per-device storage latency and swap/reclaim attribution are unverified. The package has no hardware FPS or power claim. To measure on LCD and OLED, repeat the same scene in alternating enabled/disabled runs at fixed display, TDP, FG and game settings. Compare native frame intervals, 1% lows, P95/P99, pacing, PSI and APU draw. Confirm original weight after exit, disable and a Decky crash. A manager that cannot delegate cpu.weight leaves the trial ineffective.
