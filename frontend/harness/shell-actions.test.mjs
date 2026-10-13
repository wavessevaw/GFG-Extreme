import test from "node:test";
import assert from "node:assert/strict";
import { createShellActions, shellState } from "../src/shell-actions.js";

function harness(overrides = {}) {
  const state = { enabled: true, mode: "autopilot", autopilot: { preference: "auto" },
    frame_fusion: { setting_enabled: true, scope_active: false },
    frame_os: { feature_settings: { continuous_boost: false } }, ...overrides };
  const calls = [], received = [];
  const rpc = { governor: async () => structuredClone(state) };
  for (const [name, apply] of Object.entries({
    setMode: (p, v) => { state.mode = v; }, setGovernor: (p, v) => { state.enabled = v; },
    setAutopilotPreference: (p, v) => { state.autopilot.preference = v; },
    setFrameFusion: (v) => { state.frame_fusion.setting_enabled = v; },
    setFrameOsFeature: (p, k, v) => { state.frame_os.feature_settings[k] = v; },
  })) rpc[name] = async (...args) => { calls.push([name, ...args]); apply(...args); return { success: true }; };
  const actions = createShellActions(rpc, "mako", s => received.push(s));
  return { state, calls, received, rpc, actions };
}
test("unknown saved switches stay unknown; permission is not runtime activity", () => {
  assert.equal(shellState({}).fusion, undefined);
  assert.equal(shellState({}).boost, undefined);
  const h = harness(); assert.equal(shellState(h.state).fusion, true);
  assert.equal(shellState(h.state).fusionActive, false);
});
test("start from disabled Battery selects Autopilot then enables, confirmed by readback", async () => {
  const h = harness({ mode: "budget", enabled: false });
  await h.actions.run("autopilot", true);
  assert.deepEqual(h.calls, [["setMode", "mako", "autopilot"], ["setGovernor", "mako", true]]);
  assert.equal(shellState(h.received.at(-1)).autopilot, true);
});
test("off does not stop another active governor mode", async () => {
  const h = harness({ mode: "quality" }); await h.actions.run("autopilot", false);
  assert.equal(h.calls.length, 0); assert.equal(h.state.enabled, true);
});
test("off disables actual Autopilot", async () => {
  const h = harness(); await h.actions.run("autopilot", false);
  assert.deepEqual(h.calls, [["setGovernor", "mako", false]]);
});
for (const mode of ["budget", "balanced", "quality", "extreme"]) test(`no writes for Fusion/Boost/preference in ${mode}`, async () => {
  const h = harness({ mode });
  for (const [k, v] of [["fusion", true], ["boost", true], ["preference", "battery"]])
    await assert.rejects(h.actions.run(k, v), /Enable Autopilot/);
  assert.equal(h.calls.length, 0);
});
test("stopped Autopilot blocks feature writes", async () => {
  const h = harness({ enabled: false }); await assert.rejects(h.actions.run("boost", true), /Enable/);
  assert.equal(h.calls.length, 0);
});
test("each switch uses the correct existing RPC and profile", async () => {
  const h = harness(); await h.actions.run("fusion", false); await h.actions.run("boost", true);
  await h.actions.run("preference", "smoothness");
  assert.deepEqual(h.calls, [["setFrameFusion", false], ["setFrameOsFeature", "mako", "continuous_boost", true],
    ["setAutopilotPreference", "mako", "smoothness"]]);
});
test("explicit RPC failure is displayed and state is reread", async () => {
  const h = harness(); h.rpc.setFrameFusion = async () => ({ success: false, error: "disk full" });
  await assert.rejects(h.actions.run("fusion", false), /disk full/);
  assert.equal(h.received.at(-1).frame_fusion.setting_enabled, true);
});
test("lying success cannot produce a confirmed switch", async () => {
  const h = harness(); h.rpc.setFrameFusion = async () => ({ success: true });
  await assert.rejects(h.actions.run("fusion", false), /did not confirm/);
});
test("partial start failure publishes actual saved mode without claiming enabled", async () => {
  const h = harness({ mode: "budget", enabled: false });
  h.rpc.setGovernor = async () => ({ success: false, error: "unavailable" });
  await assert.rejects(h.actions.run("autopilot", true), /unavailable/);
  assert.equal(h.received.at(-1).mode, "autopilot"); assert.equal(h.received.at(-1).enabled, false);
});
test("repeated activation is coalesced while request is pending", async () => {
  const h = harness(); let release;
  h.rpc.governor = () => new Promise(r => { release = () => r(structuredClone(h.state)); });
  const pending = h.actions.run("boost", true);
  assert.deepEqual(await h.actions.run("boost", false), { skipped: true });
  h.rpc.governor = async () => structuredClone(h.state); release(); await pending;
  assert.equal(h.calls.length, 1);
});
test("unmount during read prevents the subsequent write", async () => {
  const h = harness(); let release;
  h.rpc.governor = () => new Promise(r => { release = () => r(h.state); });
  const pending = h.actions.run("boost", true); h.actions.dispose(); release();
  await assert.rejects(pending, /Panel closed/); assert.equal(h.calls.length, 0);
});
test("bad preference does not write or switch modes", async () => {
  const h = harness(); await assert.rejects(h.actions.run("preference", "quality"), /Invalid/);
  assert.equal(h.calls.length, 0);
});
