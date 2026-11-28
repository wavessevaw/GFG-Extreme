# Reproducing the Native SR evaluation

Use GSF Kedavra commit 0a56ee93fac489fc1e34d99d7db52440778e0bd2 and Valve Gamescope aa289ea5977d8b21b92b0f246f0e8f0c225d180f. The replay links Kedavra's Vulkan host, compiles the actual compositor reconstruction function, and uses the Gamescope vendor headers for AMD EASU/RCAS and NVIDIA NVScaler. Default Gamescope sharpness 2 maps to RCAS 0.2 stops and NVIDIA 0.90. The lower-sharpening control uses 2.0 stops and 0.0. Input is opaque SDR RGBA8 with clamped texel addressing. The replay compares reconstruction mathematics; it does not reproduce all color views, workgroup layouts, HUD blending, direct scanout or presentation costs of Gamescope. All methods receive identical bytes. Software dispatch times cover compute kernels only, excluding upload and readback.

Build requirements are a C/C++ compiler, Vulkan loader and headers, glslangValidator and spirv-val. Evaluation uses Python 3, NumPy, Pillow, SciPy and FFmpeg. LPIPS is an optional offline measurement using torch 2.6.0 (CPU), torchvision 0.21.0 and lpips 0.1.4 with the v0.1 SqueezeNet calibration. These dependencies are outside the installed plugin.

Run the following from a scratch directory after exporting absolute paths for GFG, KED and GS and setting REFS to the five SHA256-verified images listed in Kedavra's kedavra/tools/detail/references.json. The photo chart uses the original pixels of astronaut, grass, brick, gravel and chelsea from scikit-image v0.25.2. Credits and licensing are recorded in the upstream dataset. The face crop shown in the examples is NASA's photograph of Eileen Collins.

```sh
TOOLS="$GFG/tools/native_sr"
LAB="$PWD"
make -C "$KED/kedavra" all
mkdir -p work softer results
(cd work && sh "$TOOLS/build.sh" "$KED" "$GS")
(cd softer && RCAS_STOPS=2.0 NIS_STRENGTH=0.0 sh "$TOOLS/build.sh" "$KED" "$GS")
for size in 1280x800 768x480 800x500 864x540 960x600 1152x720; do
  mkdir -p "scenes/$size"
  KFG_HARD_X2=1 KFG_DETAIL_SEQUENCE_OUT="$LAB/scenes/$size" \
    "$KED/kedavra/build/kfg_vktest" --spv "$KED/kedavra/build" --scaled \
    --hard --size "$size" --scene h_courtyard_reversal --json "scenes/$size/engine.json"
done
(cd work && python "$TOOLS/measure.py" "$LAB/scenes" "$REFS" "$LAB/results")
python "$TOOLS/quality_controls.py" scenes "$REFS" results/lpips.json work softer
python "$TOOLS/capture_freedoom.py" /usr/share/games/doom/freedoom2.wad captures
(cd work && python "$TOOLS/demo_replay.py" "$KED" "$LAB/captures" "$LAB/results")
(cd work && python "$TOOLS/temporal_trial.py" "$LAB/captures" "$LAB/results/history.json")
```

Freedoom Phase 2 0.13.0 and DSDA-Doom 0.29.0 rendered the same 190 input tics separately at each resolution with the stock game recorder. The lossless files have 189 frames at 35 Hz. The comparison uses aligned frames 84–105, with every second or third tick presented as a real source to the unchanged Kedavra analysis/warp harness. The high-resolution game supplies ground truth. The camera return uses Kedavra's procedural renderer with native-time references. The clips show magnified crops at reduced playback speed. Real gameplay capture happened on Linux; SteamOS/Proton, physical capture and scanout are separate tests.

Use the repository's read-only Deck recorder, for example `python tools/native_sr/record_deck.py --app 12345 --seconds 90 --out trial-01.jsonl`. Each fresh status contributes its actual native frame intervals once. APU sensor power and battery discharge are separate readings. For displayed-frame pacing use Setup's flip trace and kfg_pacing.py. For aggregate compositor GPU time use Gamescope's log_composite_timing debug channel on identical composited trials. Retain raw runs and report median, P95 and P99, thermal and power conditions, texture, virtual and physical sizes. The existing FG GPU counters do not measure the full final composite. Disable debug timings for independent power and presentation checks. Repeat on LCD and OLED with identical game scenes.
