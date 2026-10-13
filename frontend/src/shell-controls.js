import { createShellActions, shellState } from "./shell-actions.js";

export function cssLoaderEnabled(root = document.documentElement) {
  return getComputedStyle(root).getPropertyValue("--gfg-cssloader-enabled").trim() === "1";
}

export function makeShellControls(R, rpc) {
  const h = R.createElement;
  function useCssLoader() {
    const [enabled, setEnabled] = R.useState(() => cssLoaderEnabled());
    R.useEffect(() => {
      const update = () => setEnabled(cssLoaderEnabled());
      update();
      const timer = setInterval(update, 2000);
      return () => clearInterval(timer);
    }, []);
    return enabled;
  }
  function Control({ children, onClick, disabled, ...props }) {
    const F = window.DFL?.Focusable;
    const activate = disabled ? undefined : onClick;
    return F ? h(F, { ...props, "aria-disabled": disabled, onClick: activate, onActivate: activate,
      onOKButton: activate }, children) : h("button", { ...props, type: "button", disabled, "aria-disabled": disabled, onClick: activate }, children);
  }
  function Switch({ title, description, checked, disabled, onClick }) {
    return h(Control, { className: "gfg-shell-switch", role: "switch", "aria-label": title,
      "aria-checked": checked === true, disabled: disabled || typeof checked !== "boolean", onClick },
      h("span", null, h("strong", null, title), h("small", null, description)),
      h("span", { className: "gfg-shell-track" + (checked === true ? " is-on" : ""), "aria-hidden": true },
        typeof checked === "boolean" ? h("i") : "…"));
  }
  function ShellControls({ s, profile, go }) {
    const [confirmed, setConfirmed] = R.useState(s);
    const [busy, setBusy] = R.useState(false);
    const [error, setError] = R.useState("");
    const lock = R.useRef(false);
    const alive = R.useRef(true);
    const actions = R.useRef(null);
    R.useEffect(() => {
      alive.current = true;
      const controller = createShellActions(rpc, profile, (value) => {
        if (alive.current) setConfirmed(value);
      });
      actions.current = controller;
      return () => { alive.current = false; controller.dispose(); };
    }, [profile]);
    R.useEffect(() => { if (!lock.current) setConfirmed(s); }, [s]);
    const change = async (action, value) => {
      if (lock.current || !actions.current) return;
      lock.current = true; setBusy(true); setError("");
      try { await actions.current.run(action, value); }
      catch (e) { if (alive.current) setError(e.message || String(e)); }
      finally { lock.current = false; if (alive.current) setBusy(false); }
    };
    const state = shellState(confirmed);
    const disabled = busy || !profile;
    return h("section", { className: "gfg-shell-controls", "aria-busy": busy },
      h("header", null, h("strong", null, "GFG Extreme"), h("span", null, profile === "mako" ? "stable" : profile || "…")),
      h("div", { className: "gfg-shell-card" },
        h(Switch, { title: "Autopilot", description: "Автоматическая настройка производительности",
          checked: state.autopilot, disabled, onClick: () => change("autopilot", !state.autopilot) }),
        h("div", { className: "gfg-shell-priority" }, h("small", null, "Приоритет"),
          h("div", { className: "gfg-shell-segments", role: "group", "aria-label": "Приоритет Autopilot" },
            ...[["auto", "Авто"], ["battery", "Батарея"], ["smoothness", "Плавность"]].map(([v, label]) =>
              h(Control, { key: v, role: "button", "aria-pressed": state.preference === v,
                className: state.preference === v ? "selected" : "", disabled: disabled || !state.autopilot,
                onClick: () => change("preference", v) }, label))))),
      h("div", { className: "gfg-shell-card" },
        h(Switch, { title: "Frame Fusion", checked: state.fusion,
          description: state.fusionActive ? "Разрешён в Autopilot" : "Настройка сохранится; работа — в Autopilot",
          disabled: disabled || !state.autopilot, onClick: () => change("fusion", !state.fusion) }),
        h(Switch, { title: "Continuous Boost", checked: state.boost,
          description: "Постоянный буст в Autopilot · выше расход энергии",
          disabled: disabled || !state.autopilot, onClick: () => change("boost", !state.boost) })),
      busy ? h("p", { role: "status" }, "Подтверждение настроек…") : null,
      error ? h("p", { role: "alert" }, error) : null,
      confirmed.frame_fusion?.scope_update_required ? h("p", { role: "status" }, "Для Fusion обновите движок и перезапустите игру.") : null,
      h("nav", null,
        h(Control, { disabled: busy, onClick: () => go("governor") }, "Показатели"),
        h(Control, { disabled: busy, onClick: () => go("settings") }, "Настройки")),
      h("nav", { style: { marginTop: 8 } }, h(Control, { disabled: busy, onClick: () => go("classic") }, "Все режимы и управление GFG")));
  }
  return { useCssLoader, ShellControls };
}
