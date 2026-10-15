#!/usr/bin/env python3
"""Inventory reviewed open-source call sites; never reads proprietary resources.

This is a source inventory, not a C++ interpreter or a GPU trace. The dispatch
arithmetic is a reviewed model guarded by source checks and file fingerprints.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


MAKO = {
    "engine/mako-backend/src/mako.cpp": ["schedulePrepass", "scheduleFrames(std::span", "flowExtent", "createShaderRegistry", "readFrameProfile"],
    "engine/mako-backend/src/shaderchains/mipmaps.cpp": ["Mipmaps::render", "VK_FORMAT_R8_UNORM"],
    "engine/mako-backend/src/shaderchains/alpha0.cpp": ["Alpha0::render"],
    "engine/mako-backend/src/shaderchains/alpha1.cpp": ["Alpha1::render"],
    "engine/mako-backend/src/shaderchains/beta0.cpp": ["Beta0::render"],
    "engine/mako-backend/src/shaderchains/beta1.cpp": ["Beta1::render"],
    "engine/mako-backend/src/shaderchains/gamma0.cpp": ["Gamma0::render"],
    "engine/mako-backend/src/shaderchains/gamma1.cpp": ["Gamma1::render", "prepassScratch"],
    "engine/mako-backend/src/shaderchains/delta0.cpp": ["Delta0::render"],
    "engine/mako-backend/src/shaderchains/delta1.cpp": ["Delta1::render", "deltaScratch"],
    "engine/mako-backend/src/shaderchains/generate.cpp": ["Generate::render", "dispatchExtent"],
    "engine/mako-backend/src/extraction/shader_registry.cpp": ["buildShaderRegistry"],
    "engine/mako-backend/src/extraction/lsfg_shader_set.cpp": ["loadLsfgShaderSet", "translator.translate"],
    "engine/mako-backend/src/helpers/managed_shader.cpp": ["VK_QUEUE_FAMILY_IGNORED", "ManagedShader::dispatch"],
    "engine/mako-backend/src/helpers/temporal_phases.hpp": ["alphaHistoryCounts", "std::lcm"],
    "engine/mako-render/src/entrypoint.cpp": ["myvkQueuePresentKHR"],
    "engine/mako-render/src/swapchain/resources.cpp": ["sourceFds", "openContext", "effectiveFlowScale"],
    "engine/mako-render/src/swapchain/present/generated_frames.cpp": ["blitImage", "presentGeneratedFrames"],
    "engine/mako-render/src/swapchain/present/admission.cpp": ["recoverBackendIfReady", "prepareFramePlan"],
    "engine/mako-render/src/adaptive_scheduler.cpp": ["desiredOutputsPerRealFrame"],
    "engine/mako-cli/src/tools/quality.cpp": ["runTemporal", "sequence.tsv"],
    "engine/mako-cli/src/tools/benchmark.cpp": ["benchmark::run"],
}
GFG = {
    "engine/gfg-temporal/src/te_lmc.inc": ["lmc_fit_job", "vkWaitSemaphores", "slot->lmc_fit_ms", "lmc_record_analysis", "lmc_record_output"],
    "engine/gfg-temporal/src/te_engine.c": ["te_context_idle", "ready_ms"],
    "engine/gfg-temporal/mako/gfg_temporal.cpp": ["Prepared::openExperimental", "Prepared::attach", "LSFG keeps"],
    "engine/gfg-fusion/renderer.patch": ["this->m_temporal =", "parseMode(std::getenv"],
    "docs/TEMPORAL_ENGINE_BENCHMARK.md": ["lavapipe"],
}


def inventory(root, selected):
    result = {}
    for name, anchors in selected.items():
        file = root / name
        if not file.is_file():
            result[name] = {"available": False}
            continue
        raw = file.read_bytes()
        lines = raw.decode().splitlines()
        result[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "line_count": len(lines),
                        "anchors": {a: [n for n, line in enumerate(lines, 1) if a in line] for a in anchors}}
    return result


def reviewed_dispatch_model(root):
    backend = root / "engine/mako-backend/src"
    observed = {}
    expected = {"mipmaps": 1, "alpha0": 3, "alpha1": 1, "beta0": 1, "beta1": 4,
                "gamma0": 1, "gamma1": 4, "delta0": 2, "delta1": 8, "generate": 1}
    for chain in expected:
        text = (backend / f"shaderchains/{chain}.cpp").read_text()
        render = text[text.index("::render("):]
        if re.search(r"for\s*\(const auto& set : this->sets\)", render):
            count = text.count("this->sets.emplace_back(")
        else:
            count = render.count(".dispatch(")
        observed[chain] = count
    source = (backend / "mako.cpp").read_text()
    checks = {"chain_counts_match": observed == expected,
              "seven_levels_present": "< 7;" in source,
              "three_delta_levels_present": "if (j < 4) continue;" in source,
              "prepass_called": "this->schedulePrepass(VK_NULL_HANDLE);" in source}
    ok = all(checks.values())
    return {"evidence": "SOURCE VERIFIED" if ok else "NOT TESTED",
            "model": "reviewed SDR full-generation path; no HDR conversion; no runtime trace",
            "checks": checks, "dispatches_per_chain_call": observed,
            "prepass_dispatches": 34 if ok else None,
            "per_output_dispatches": 66 if ok else None,
            "note": "Counts are not GPU time, occupancy, shader workgroup size or image quality."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mako-base", type=Path, required=True)
    p.add_argument("--mako-current", type=Path, required=True)
    p.add_argument("--gfg", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = {"schema": 1, "purpose": "source-inventory-not-hardware-benchmark",
              "mako_base": inventory(args.mako_base, MAKO),
              "mako_current": inventory(args.mako_current, MAKO),
              "gfg": inventory(args.gfg, GFG),
              "dispatch_models": {"base": reviewed_dispatch_model(args.mako_base),
                                  "current": reviewed_dispatch_model(args.mako_current)}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["dispatch_models"], indent=2))


if __name__ == "__main__":
    main()
