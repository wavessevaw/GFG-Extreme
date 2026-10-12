"""Bounded evidence of the actual mapped renderer file, separate from installed files."""
from __future__ import annotations

from functools import lru_cache
import hashlib
import os
from pathlib import Path
import stat

RENDERER_LIBRARIES = frozenset(("libmako-render.so", "libmako-render-scaling.so"))
MAX_RENDERER_BYTES = 64 * 1024 * 1024


def process_start_ticks(proc: Path) -> int | None:
    try:
        value = (proc / "stat").read_text()
        command_end = value.rfind(")")
        if command_end < 0:
            return None
        fields = value[command_end + 2:].split()
        return int(fields[19])
    except (OSError, ValueError, IndexError):
        return None


def _fingerprint(st: os.stat_result) -> tuple:
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


@lru_cache(maxsize=32)
def _hash_file(path: str, fingerprint: tuple) -> dict:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or _fingerprint(before) != fingerprint
                or not 20 <= before.st_size <= MAX_RENDERER_BYTES):
            raise ValueError("renderer-file-changed-or-invalid")
        digest = hashlib.sha256()
        header = b""
        total = 0
        while total <= MAX_RENDERER_BYTES:
            data = os.read(fd, min(1024 * 1024, MAX_RENDERER_BYTES + 1 - total))
            if not data:
                break
            if not header:
                header = data[:20]
            total += len(data)
            digest.update(data)
        if total != before.st_size or _fingerprint(os.fstat(fd)) != fingerprint:
            raise ValueError("renderer-file-changed-during-hash")
        if header[:4] != b"\x7fELF" or header[4] not in (1, 2) or header[5] not in (1, 2):
            raise ValueError("renderer-file-not-elf")
        return {"sha256": digest.hexdigest(), "elf_bits": 64 if header[4] == 2 else 32,
            "elf_machine": int.from_bytes(header[18:20], "little" if header[5] == 1 else "big"),
            "size": total}
    finally:
        os.close(fd)


def mapped_renderer_files(proc: Path, maps: str) -> list[dict]:
    """Never hash a replacement at the same pathname as if it were the mapped file.

    Prefer map_files (also works across mount namespaces). If permissions deny it,
    accept only a pathname whose device/inode match /proc/maps. Deleted mappings
    require map_files; a new installed file is not evidence of the running engine.
    """
    result = []
    seen = set()
    for line in maps.splitlines():
        fields = line.split(None, 5)
        if len(fields) != 6:
            continue
        address, _, _, device, inode_text, mapped_path = fields
        path = mapped_path.removesuffix(" (deleted)")
        if Path(path).name not in RENDERER_LIBRARIES or path in seen:
            continue
        seen.add(path)
        record = {"path": path, "state": "unavailable", "basis": None}
        try:
            inode = int(inode_text)
            major, minor = (int(v, 16) for v in device.split(":"))
            if inode <= 0:
                raise ValueError("mapping-has-no-file-identity")
            candidates = [(proc / "map_files" / address, "mapped-file")]
            if mapped_path == path:
                candidates.append((Path(path), "mapped-path-inode"))
            for candidate, basis in candidates:
                try:
                    st = candidate.stat()
                    if (st.st_ino != inode or os.major(st.st_dev) != major or os.minor(st.st_dev) != minor):
                        raise ValueError("mapped-file-identity-mismatch")
                    identity = _hash_file(str(candidate), _fingerprint(st))
                    # Even a cached result must still name the same unchanged file.
                    if _fingerprint(candidate.stat()) != _fingerprint(st):
                        raise ValueError("renderer-file-changed-during-probe")
                    record.update(identity, state="verified", basis=basis, inode=inode,
                        device=device, mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns)
                    break
                except (OSError, ValueError) as error:
                    record["reason"] = str(error)[:240]
            if record["state"] == "verified":
                record.pop("reason", None)
        except (ValueError, TypeError) as error:
            record["reason"] = str(error)[:240]
        result.append(record)
        if len(result) == len(RENDERER_LIBRARIES):
            break
    return result
