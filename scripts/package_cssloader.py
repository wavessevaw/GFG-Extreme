"""Package only the theme, with reproducible archive metadata and a SHA-256.

Does not download dependencies or alter a user's CSS Loader profile.
Run from any directory: python scripts/package_cssloader.py [output-directory]
"""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
theme = root / "themes" / "GFG-SteamOS"
manifest = json.loads((theme / "theme.json").read_text(encoding="utf-8"))
for name in manifest["inject"]:
    if Path(name).name != name or not (theme / name).is_file():
        raise SystemExit(f"Invalid theme file: {name}")
output = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "artifacts"
output.mkdir(parents=True, exist_ok=True)
archive = output / f"GFG-SteamOS-CSSLoader-{manifest['version']}.zip"
files = sorted(p for p in theme.iterdir() if p.is_file())
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for source in files:
        info = zipfile.ZipInfo("GFG-SteamOS/" + source.name, (2026, 10, 14, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, source.read_bytes())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
print(f"{archive}\nSHA256 {digest}\nTheme only; plugin companion is built separately.")
