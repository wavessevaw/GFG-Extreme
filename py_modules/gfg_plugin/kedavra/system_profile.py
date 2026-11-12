# SPDX-License-Identifier: GPL-3.0-or-later
"""KEDAVRA system profile (GFG Extreme 3.3.0): the kernel's memory, scheduler and storage
settings tuned for games, installed with the engine and removed with it.

Only runtime kernel settings (/proc/sys, /sys) are written, from the same boot unit that mounts
Gamescope KEDAVRA: nothing in the read-only system image, no kernel command line, no driver or
package changes, no security mitigations touched. Every value is saved before it is written
(in /run, so per boot), Remove writes the saved values back at once, and the next boot is
stock anyway. A path a SteamOS release does not have is skipped.

What it changes and why:
  * memory: transparent huge pages for game memory (fewer TLB misses), reclaim started early
    with a larger free reserve and proactive compaction off (no allocation stalls in a scene),
    swap tuned for zram (no read-ahead, preferred over dropping file cache), MGLRU
    thrash protection, KSM off, writeback in smaller, earlier bursts;
  * CPU: no autogroup (the game is not one equal group among Steam's helpers), no lockup
    watchdogs and fewer vmstat wakeups (fewer timer interrupts on the game's cores);
  * storage: kyber on NVMe and BFQ on microSD with low read latency targets, 1 MiB read-ahead
    for asset streaming, completions on the submitting core.
"""
from __future__ import annotations

from pathlib import Path
from shlex import quote

# (path or glob, value, condition). Conditions: "zram" = a zram swap is active.
SETTINGS = (
    ("/proc/sys/kernel/sched_autogroup_enabled", "0", None),
    ("/proc/sys/kernel/watchdog", "0", None),
    ("/proc/sys/kernel/nmi_watchdog", "0", None),
    ("/proc/sys/vm/compaction_proactiveness", "0", None),
    ("/proc/sys/vm/compact_unevictable_allowed", "1", None),
    ("/proc/sys/vm/extfrag_threshold", "750", None),
    ("/proc/sys/vm/min_free_kbytes", "131072", None),
    ("/proc/sys/vm/watermark_boost_factor", "5000", None),
    ("/proc/sys/vm/watermark_scale_factor", "125", None),
    ("/proc/sys/vm/dirty_background_bytes", "209715200", None),
    ("/proc/sys/vm/dirty_bytes", "419430400", None),
    ("/proc/sys/vm/dirty_expire_centisecs", "1500", None),
    ("/proc/sys/vm/dirty_writeback_centisecs", "500", None),
    ("/proc/sys/vm/vfs_cache_pressure", "50", None),
    ("/proc/sys/vm/stat_interval", "15", None),
    ("/proc/sys/vm/swappiness", "150", "zram"),
    ("/proc/sys/vm/page-cluster", "0", "zram"),
    ("/sys/kernel/mm/ksm/run", "0", None),
    ("/sys/kernel/mm/lru_gen/enabled", "0x0007", None),
    ("/sys/kernel/mm/lru_gen/min_ttl_ms", "200", None),
    ("/sys/kernel/mm/swap/vma_ra_enabled", "false", "zram"),
    ("/sys/kernel/mm/transparent_hugepage/enabled", "always", None),
    ("/sys/kernel/mm/transparent_hugepage/defrag", "defer+madvise", None),
    ("/sys/kernel/mm/transparent_hugepage/shmem_enabled", "within_size", None),
    ("/sys/kernel/mm/transparent_hugepage/khugepaged/defrag", "1", None),
    ("/sys/kernel/mm/transparent_hugepage/khugepaged/pages_to_scan", "2048", None),
    ("/sys/kernel/mm/transparent_hugepage/khugepaged/scan_sleep_millisecs", "8000", None),
    ("/sys/kernel/mm/transparent_hugepage/khugepaged/alloc_sleep_millisecs", "30000", None),
    ("/sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none", "409", None),
    ("/sys/block/nvme*n*/queue/scheduler", "kyber", None),
    ("/sys/block/nvme*n*/queue/iosched/read_lat_nsec", "1000000", None),
    ("/sys/block/nvme*n*/queue/iosched/write_lat_nsec", "3500000", None),
    ("/sys/block/nvme*n*/queue/read_ahead_kb", "1024", None),
    ("/sys/block/nvme*n*/queue/rq_affinity", "2", None),
    ("/sys/block/nvme*n*/queue/add_random", "0", None),
    ("/sys/block/nvme*n*/queue/wbt_lat_usec", "0", None),
    ("/sys/block/mmcblk*/queue/scheduler", "bfq", None),
    ("/sys/block/mmcblk*/queue/iosched/slice_idle", "0", None),
    ("/sys/block/mmcblk*/queue/iosched/fifo_expire_sync", "80", None),
    ("/sys/block/mmcblk*/queue/iosched/timeout_sync", "100", None),
    ("/sys/block/mmcblk*/queue/iosched/back_seek_penalty", "1", None),
    ("/sys/block/mmcblk*/queue/nr_requests", "64", None),
    ("/sys/block/mmcblk*/queue/read_ahead_kb", "1024", None),
    ("/sys/block/mmcblk*/queue/rq_affinity", "2", None),
    ("/sys/block/mmcblk*/queue/add_random", "0", None),
    ("/sys/block/mmcblk*/queue/wbt_lat_usec", "0", None),
    ("/sys/block/zram*/queue/read_ahead_kb", "0", None),
    ("/sys/block/zram*/queue/nomerges", "2", None),
    ("/sys/block/zram*/queue/add_random", "0", None),
)

# Games that lock memory for their audio or anti-cheat get room for it (read at login).
LIMITS_NAME = "90-kedavra-memlock.conf"
LIMITS = "# KEDAVRA system profile (GFG Extreme): removed with the engine\n* hard memlock 2147484\n* soft memlock 2147484\n"

# The script runs as root at boot (and once at install). ORIG keeps "path<TAB>value" of every
# file before its first write in this boot; a choice file reads "[mq-deadline] kyber" or
# "always [madvise] never" and keeps the bracketed one.
TUNE_SH = r"""#!/bin/sh
# KEDAVRA system profile (written by the GFG Extreme plugin). Runtime kernel settings only.
ORIG={orig}
DONE={done}
[ -f "{state}/profile_off" ] && exit 0
# The boot watchdog disables the engine before this script runs; do not apply
# its system profile after that rollback or while the engine is disabled.
[ -f "{state}/disabled" ] && exit 0
mkdir -p "$(dirname "$ORIG")"
touch "$ORIG"
zram=0
grep -q '^/dev/zram' /proc/swaps 2>/dev/null && zram=1
ok=0; fail=0
put() {{
	for f in $1; do
		[ -f "$f" ] || continue
		if ! grep -q "^$f	" "$ORIG"; then
			old=$(cat "$f" 2>/dev/null) || continue
			case "$old" in *\[*\]*) old=$(printf '%s' "$old" | sed -n 's/.*\[\(.*\)\].*/\1/p');; esac
			printf '%s\t%s\n' "$f" "$old" >> "$ORIG"
		fi
		if printf '%s\n' "$2" > "$f" 2>/dev/null; then ok=$((ok+1)); else fail=$((fail+1)); fi
	done
}}
{lines}
echo "applied=$ok failed=$fail zram=$zram" > "$DONE"
"""

RESTORE_SH = r"""#!/bin/sh
# KEDAVRA system profile: write the saved values back (Remove, or the profile switched off).
ORIG={orig}
[ -f "$ORIG" ] || exit 0
# Restore dependent iosched settings before switching their scheduler back.
# Stop at the first failure, preserving it and all earlier entries for retry.
umask 077
work=$(mktemp -d "${{ORIG}}.restore.XXXXXX") || exit 1
trap 'rm -rf "$work"' EXIT
tac "$ORIG" > "$work/reverse" || exit 1
: > "$work/pending"
failed=0
while IFS="	" read -r f v; do
	if [ "$failed" = 0 ]; then
		if [ -f "$f" ] && (printf '%s\n' "$v" > "$f") 2>/dev/null; then
			actual=$(cat "$f" 2>/dev/null) || actual='__read_failed__'
			case "$actual" in *\[*\]*) actual=$(printf '%s' "$actual" | sed -n 's/.*\[\(.*\)\].*/\1/p');; esac
			[ "$actual" = "$v" ] && continue
		fi
		echo "KEDAVRA: could not restore $f; journal retained for retry" >&2
		failed=1
	fi
	printf '%s\t%s\n' "$f" "$v" >> "$work/pending" || exit 1
done < "$work/reverse"
if [ "$failed" != 0 ]; then
	tac "$work/pending" > "$work/orig" && mv "$work/orig" "$ORIG"
	exit 1
fi
rm -f "$ORIG" {done}
"""


def tune_script(state: Path, orig: Path, done: Path) -> str:
    lines = []
    for path, value, cond in SETTINGS:
        call = f"put '{path}' '{value}'"
        lines.append(f'[ "$zram" = 1 ] && {call}' if cond == "zram" else call)
    return TUNE_SH.format(state=state, orig=orig, done=done, lines="\n".join(lines))


def restore_script(orig: Path, done: Path) -> str:
    return RESTORE_SH.format(orig=quote(str(orig)), done=quote(str(done)))
