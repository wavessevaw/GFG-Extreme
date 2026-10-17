#!/usr/bin/env python3
"""Exercise the EXACT full-size installed LAB zip with an isolated home.

This is launcher-level testing. It does NOT execute a real Vulkan game on Deck.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(command, env, *, result=0):
    outcome = subprocess.run(command, env=env, text=True, capture_output=True,
                             timeout=40)
    if outcome.returncode != result:
        raise AssertionError((command, outcome.returncode,
                              outcome.stdout[-1200:], outcome.stderr[-1200:]))
    return outcome


def observed(launcher, mode, env, *, inherited=False):
    clean = dict(env)
    if inherited:
        clean["VK_INSTANCE_LAYERS"] = "VK_LAYER_GFG_native:VK_LAYER_KHRONOS_validation"
        clean["GFG_NATIVE_FG"] = "1"
        clean["GFG_NATIVE_GPU_BRIDGE"] = "1"
    code = (
        "import json,os;"
        "keys=['VK_INSTANCE_LAYERS','GFG_NATIVE_FG','GFG_NATIVE_MODE',"
        "'DISABLE_GFG_NATIVE_FG','DISABLE_MAKO','GFG_NATIVE_GPU_BRIDGE'];"
        "print(json.dumps({k:os.environ.get(k) for k in keys}))"
    )
    out = run(["bash", str(launcher), mode, sys.executable, "-c", code], clean)
    return json.loads(out.stdout.strip().splitlines()[-1]), out.stderr


def main():
    p = argparse.ArgumentParser()
    p.add_argument("zip", type=Path)
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix="gfg-gsf-lab-") as tmp:
        root = Path(tmp)
        dest = root / "install"
        dest.mkdir()
        with zipfile.ZipFile(args.zip) as archive:
            assert archive.testzip() is None
            archive.extractall(dest)
            for info in archive.infolist():
                if info.is_dir():
                    continue
                path = dest / info.filename
                path.chmod((info.external_attr >> 16) & 0o777)
        home = root / "home"
        home.mkdir()
        plugin = dest / "GFG-Extreme"
        wrapper = plugin / "bin/gfg-native/gfg-gsf-lab.sh"
        assert wrapper.is_file() and os.access(wrapper, os.X_OK)
        # An unexpanded placeholder must never create a fake Vulkan failure.
        env_placeholder = dict(os.environ, HOME=str(root / "home"))
        for mode in ("--off", "--x2", "--x3"):
            rejected = run(["bash", str(wrapper), mode, "%command%"],
                           env_placeholder, result=2)
            assert "did not expand" in rejected.stderr
        native = plugin / "bin/gfg-native"
        manifest = json.loads((native / "MANIFEST.json").read_text())
        env = dict(os.environ)
        env.update(HOME=str(home), XDG_DATA_HOME=str(home / ".local/share"),
                   XDG_STATE_HOME=str(home / ".local/state"),
                   XDG_CONFIG_HOME=str(home / ".config"))
        for key in list(env):
            if key.startswith("GFG_NATIVE_"):
                env.pop(key)
        # Crucial: installing the plugin ZIP must not touch the native loader.
        assert not (home / ".local/bin/gfg-native").exists()
        result, _ = observed(wrapper, "--off", env, inherited=True)
        assert result["GFG_NATIVE_FG"] is None
        assert result["DISABLE_GFG_NATIVE_FG"] == "1"
        assert result["VK_INSTANCE_LAYERS"] == "VK_LAYER_KHRONOS_validation"
        assert not (home / ".local/share/gfg-native").exists()
        print("PASS: ZIP install does not activate GSF; Off strips inherited native layer", flush=True)
        result, warning = observed(wrapper, "--x2", env)
        assert result["GFG_NATIVE_FG"] is None
        assert "not installed" in warning
        print("PASS: missing experimental binary fails open and starts command", flush=True)
        install = run(["bash", str(wrapper), "--install"], env)
        assert "installed" in install.stdout.lower()
        installed = home / ".local/share/gfg-native"
        binary = installed / "libVkLayer_gfg_native.so"
        assert binary.exists() and sha(binary.read_bytes()) == manifest["elf_sha256"]
        for mode, clock in [("--x2", "2"), ("--x3", "3")]:
            result, _ = observed(wrapper, mode, env)
            assert result["GFG_NATIVE_MODE"] == clock
            assert result["GFG_NATIVE_FG"] == "1"
            assert "VK_LAYER_GFG_native" in result["VK_INSTANCE_LAYERS"]
            assert result["DISABLE_MAKO"] == "1"
            print("PASS: explicit " + mode + " enters opt-in native layer", flush=True)
        result, _ = observed(wrapper, "--off", env, inherited=True)
        assert result["GFG_NATIVE_FG"] is None
        assert result["DISABLE_GFG_NATIVE_FG"] == "1"
        assert result["VK_INSTANCE_LAYERS"] == "VK_LAYER_KHRONOS_validation"
        print("PASS: Off remains strict after GSF installation", flush=True)
        run(["bash", str(native / "rollback.sh")], env)
        assert not binary.exists()
        result, _ = observed(wrapper, "--off", env)
        assert result["DISABLE_GFG_NATIVE_FG"] == "1"
        print("PASS: rollback restores safe launch", flush=True)
        pkg = json.loads((plugin / "package.json").read_text())
        assert pkg["gsfLab"]["enabled_by_default"] is False
        assert pkg["base_version"] == "2.1.6"
        print("PASS: staged full plugin metadata safe, no physical Deck claim", flush=True)


if __name__ == "__main__":
    main()
