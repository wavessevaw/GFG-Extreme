// The shell is a client of the existing RPCs, never a second governor.
export function shellState(status) {
  const s = status || {};
  return {
    autopilot: s.enabled === true && s.mode === "autopilot",
    mode: s.mode,
    preference: s.autopilot?.preference,
    fusion: s.frame_fusion?.setting_enabled,
    fusionActive: s.frame_fusion?.scope_active === true,
    boost: s.frame_os?.feature_settings?.continuous_boost,
  };
}

export function createShellActions(rpc, profile, receive) {
  let busy = false, disposed = false;
  const check = () => { if (disposed) throw new Error("Panel closed; reopen it to check the saved state."); };
  const read = async () => {
    check();
    const s = await rpc.governor(profile);
    check();
    if (!s || s.success === false || typeof s.enabled !== "boolean" || !s.mode)
      throw new Error(s?.error || "Governor state unavailable");
    receive(s);
    return s;
  };
  const write = async (fn, ...args) => {
    check();
    const r = await fn(...args);
    check();
    if (!r || r.success === false) throw new Error(r?.error || r?.message || "Setting was not accepted");
  };
  return {
    dispose() { disposed = true; },
    async run(action, value) {
      if (busy) return { skipped: true };
      if (!profile) throw new Error("Select a profile first");
      busy = true;
      try {
        const before = await read();
        const state = shellState(before);
        if (action === "autopilot") {
          if (typeof value !== "boolean") throw new Error("Invalid Autopilot setting");
          if (value) {
            if (before.mode !== "autopilot") await write(rpc.setMode, profile, "autopilot");
            if (!before.enabled) await write(rpc.setGovernor, profile, true);
          } else if (state.autopilot) {
            await write(rpc.setGovernor, profile, false);
          }
        } else {
          if (!state.autopilot) throw new Error("Enable Autopilot first");
          if (action === "preference") {
            if (!["auto", "battery", "smoothness"].includes(value)) throw new Error("Invalid preference");
            await write(rpc.setAutopilotPreference, profile, value);
          } else if (action === "fusion" || action === "boost") {
            if (typeof value !== "boolean") throw new Error("Invalid switch setting");
            if (action === "fusion") await write(rpc.setFrameFusion, value);
            else await write(rpc.setFrameOsFeature, profile, "continuous_boost", value);
          } else throw new Error("Unknown shell action");
        }
        const after = shellState(await read());
        if (after[action] !== value) throw new Error("Backend did not confirm the requested setting");
        return { success: true };
      } catch (e) {
        // Even partially completed multi-step requests show the actual saved state.
        if (!disposed) { try { await read(); } catch {} }
        throw e;
      } finally { busy = false; }
    },
  };
}
