## Быстрые настройки (View button), mockup 04: Яркость, Громкость, Wi-Fi, then the GFG
## block (Autopilot, Frame Fusion, Continuous Boost) and Сон. Every GFG switch is one
## Governor setting through the Bridge; the shell itself never changes power limits.
class_name QuickSettings
extends Overlay

var _bright: GSliderRow
var _vol: GSliderRow
var _wifi: Button
var _auto: Button
var _fusion: Button
var _boost: Button
var _auto_sw: GSwitch
var _fusion_sw: GSwitch
var _boost_sw: GSwitch
var _short: Button
var _short_sw: GSwitch
var _ring: GRing
var _flow: Label
var _flow_x: Label
var _goal: Label
var _badge: Label
var _pw_ring: GRing
var _pw: Label
var _bat_ring: GRing
var _bat: Label
var _auto_sub: Label
var _status: Label
var _clock: Label
var _last_manual_mode := "balanced"


func _ready() -> void:
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.45)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var p := UI.panel(Color(0.067, 0.067, 0.086), 18, 0)
	var ps: StyleBoxFlat = p.get_theme_stylebox("panel")
	ps.shadow_color = Color(0, 0, 0, 0.55)
	ps.shadow_size = 40
	ps.border_width_right = 0
	ps.border_width_top = 0
	ps.border_width_bottom = 0
	p.set_anchors_and_offsets_preset(Control.PRESET_RIGHT_WIDE)
	p.offset_left = -560
	sheet = p
	sheet_from = Vector2(140, 0)
	add_child(p)
	var v := UI.vbox(10)
	p.add_child(UI.margin(v, 6, 10, 6, 10))
	var head := UI.hbox(14)
	head.add_child(UI.label("Быстрые настройки", 26, UI.TEXT, "bold"))
	head.add_child(UI.spacer())
	_status = UI.label("", 16, UI.TEXT, "medium")
	head.add_child(_status)
	_clock = UI.label("", 17, UI.TEXT, "bold")
	head.add_child(_clock)
	v.add_child(head)
	var c1 := UI.panel(UI.CARD, 6, 14)
	var v1 := UI.vbox(2)
	c1.add_child(v1)
	_bright = GSliderRow.make("sun", "Яркость", SystemInfo.brightness_pct())
	_bright.value_committed.connect(func(val):
		if not SystemInfo.set_brightness_pct(val):
			app.toast("Яркостью управляет Steam: кнопка «…» → Яркость"))
	v1.add_child(_bright)
	_vol = GSliderRow.make("volume", "Громкость", SystemInfo.volume_pct())
	_vol.value_committed.connect(func(val):
		if not SystemInfo.set_volume_pct(val):
			app.toast("Не удалось изменить громкость")
		var now := SystemInfo.volume_pct()
		if now >= 0:
			_vol.set_value(now))
	v1.add_child(_vol)
	_wifi = UI.row("wifi", "Wi-Fi", "", UI.label("", 15, UI.TEXT_DIM, "medium"), 58)
	_wifi.pressed.connect(func(): close(); OS.create_process(GameRunner.steam_command(), ["steam://open/settings/internet"]))
	v1.add_child(_wifi)
	v.add_child(c1)
	v.add_child(UI.margin(UI.kicker("GFG"), 6, 10, 0, 2))
	# GFG: the plugin's rings (FPS with the wolf, power, battery) and its switches as tiles
	var hero := UI.panel(UI.CARD, 14, 14)
	var hh := UI.hbox(16)
	hero.add_child(hh)
	_ring = GRing.make(118, 9, UI.RED)
	_ring.wolf = true
	_ring.text_size = 34
	hh.add_child(_ring)
	var hv := UI.vbox(4)
	hv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hv.alignment = BoxContainer.ALIGNMENT_CENTER
	hv.add_child(_small("РЕАЛЬНЫЕ × GFG"))
	var fl := UI.hbox(8)
	_flow = UI.label("—", 30, UI.TEXT, "bold")
	_flow_x = UI.label("", 30, UI.RED, "bold")
	fl.add_child(_flow)
	fl.add_child(_flow_x)
	hv.add_child(fl)
	_goal = _small("")
	hv.add_child(_goal)
	_badge = UI.label("", 13, UI.TEXT_DIM, "bold")
	hv.add_child(_badge)
	hh.add_child(hv)
	var minis := UI.vbox(10)
	minis.alignment = BoxContainer.ALIGNMENT_CENTER
	var m1 := _mini("bolt", Color("ff8a3d"))
	_pw_ring = m1[0]
	_pw = m1[1]
	minis.add_child(m1[2])
	var m2 := _mini("battery", UI.GREEN)
	_bat_ring = m2[0]
	_bat = m2[1]
	minis.add_child(m2[2])
	hh.add_child(minis)
	v.add_child(hero)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 10)
	grid.add_theme_constant_override("v_separation", 10)
	_auto_sw = GSwitch.make(false)
	_auto = _tile("gauge", "Autopilot", "Подбирает FPS и мощность", _auto_sw)
	_auto_sub = _auto.get_meta("sub")
	_auto.pressed.connect(_toggle_autopilot)
	grid.add_child(_auto)
	_fusion_sw = GSwitch.make(false)
	_fusion = _tile("layers", "Frame Fusion", "Плавнее кадры GFG", _fusion_sw)
	_fusion.pressed.connect(func():
		Shell.bridge.set_frame_fusion(not bool(Shell.bridge.status.get("frame_fusion", {}).get("setting", false)), _result))
	grid.add_child(_fusion)
	_short_sw = GSwitch.make(false)
	_short = _tile("bolt", "Boost", "Больше кадров в тяжёлых сценах", _short_sw)
	_short.pressed.connect(func():
		Shell.bridge.set_boost(not bool(Shell.bridge.status.get("boost", true)), _result))
	grid.add_child(_short)
	_boost_sw = GSwitch.make(false)
	_boost = _tile("refresh", "Continuous Boost", "Постоянно · больше энергии", _boost_sw)
	_boost.pressed.connect(func():
		Shell.bridge.set_continuous_boost(not bool(Shell.bridge.status.get("continuous_boost", false)), _result))
	grid.add_child(_boost)
	v.add_child(grid)
	var c3 := UI.panel(UI.CARD, 6, 14)
	var sleep := UI.row("power", "Сон", "", GIcon.make("chevron", 18, UI.TEXT_DIM), 58)
	sleep.pressed.connect(func(): close(); SystemInfo.power("suspend"))
	c3.add_child(sleep)
	v.add_child(c3)
	Shell.bridge.status_updated.connect(func(_s): if visible: _refresh_gfg())
	Shell.bridge.connection_changed.connect(func(_c): if visible: _refresh_gfg())


func _on_open() -> void:
	_bright.available = SystemInfo.brightness_pct() >= 0
	_bright.set_value(max(SystemInfo.brightness_pct(), 0))
	var vp := SystemInfo.volume_pct()
	_vol.available = vp >= 0
	_vol.set_value(max(vp, 0))
	var ssid := SystemInfo.wifi_name()
	var net := SystemInfo.network()
	var val: Label = _wifi.get_child(0).get_child(0).get_child(2)
	val.text = ssid if ssid != "" else ("подключено" if net.get("online", false) else "нет сети")
	var b := SystemInfo.battery()
	_status.text = ("%d%%" % b.percent) if b.available else ""
	_clock.text = Time.get_time_string_from_system().substr(0, 5)
	_refresh_gfg()


func _refresh_gfg() -> void:
	var on := Shell.bridge.connected
	var s := Shell.bridge.status
	for r in [_auto, _fusion, _boost, _short]:
		r.disabled = not on
		r.modulate.a = 1.0 if on else 0.55
	_auto_sw.unknown = not on
	_fusion_sw.unknown = not on
	_boost_sw.unknown = not on
	_short_sw.unknown = not on
	_short_sw.on = bool(s.get("boost", true))
	_update_rings(on, s)
	var mode := str(s.get("mode", ""))
	if mode != "" and mode != "autopilot":
		_last_manual_mode = mode
	_auto_sw.on = mode == "autopilot"
	_fusion_sw.on = bool(s.get("frame_fusion", {}).get("setting", false))
	_boost_sw.on = bool(s.get("continuous_boost", false))
	_auto_sub.text = "Подбирает FPS и мощность" if on else "GFG Extreme не подключён"


func _toggle_autopilot() -> void:
	var mode := str(Shell.bridge.status.get("mode", ""))
	Shell.bridge.set_mode(_last_manual_mode if mode == "autopilot" else "autopilot", _result)


func _result(ok: bool, r: Dictionary) -> void:
	if not ok:
		app.toast("GFG: %s" % r.get("error", "ошибка"))
	Shell.bridge.call_method("status", {}, func(ok2, st):
		if ok2:
			Shell.bridge.status = st
			Shell.bridge.status_updated.emit(st))


func _small(t: String) -> Label:
	var l := UI.label(t, 12, UI.TEXT_DIM, "bold")
	l.add_theme_font_override("font", UI.tracked("bold", 2))
	return l


## A small ring with an icon, and its value beside it.
func _mini(icon: String, col: Color) -> Array:
	var h := UI.hbox(8)
	var r := GRing.make(40, 5, col)
	r.icon = icon
	var holder := Control.new()
	holder.custom_minimum_size = Vector2(40, 40)
	holder.add_child(r)
	r.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var ic := GIcon.make(icon, 14, col)
	ic.custom_minimum_size = Vector2(14, 14)
	ic.size = Vector2(14, 14)
	ic.position = Vector2(13, 13)
	holder.add_child(ic)
	h.add_child(holder)
	var l := UI.label("—", 16, UI.TEXT, "bold")
	l.custom_minimum_size = Vector2(62, 0)
	h.add_child(l)
	return [r, l, h]


## A switch tile: icon disc and switch on top, title and one line under them.
func _tile(icon: String, title: String, sub: String, sw: GSwitch) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.custom_minimum_size = Vector2(0, 92)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var sb := UI.box(Color(1, 1, 1, 0.035), Color(1, 1, 1, 0.07), 14)
	for st in ["normal", "pressed", "disabled"]:
		b.add_theme_stylebox_override(st, sb)
	b.add_theme_stylebox_override("hover", UI.box(Color(1, 1, 1, 0.06), Color(1, 1, 1, 0.09), 14))
	b.add_theme_stylebox_override("focus", UI.focus_box(UI.RED, 14))
	var col := UI.vbox(4)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var m := UI.margin(col, 14, 12, 14, 10)
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(m)
	var top := UI.hbox(8)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var disc := Panel.new()
	disc.custom_minimum_size = Vector2(30, 30)
	disc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	disc.add_theme_stylebox_override("panel", UI.box(Color(UI.RED, 0.16), Color.TRANSPARENT, 9))
	var ic := GIcon.make(icon, 16, UI.RED.lightened(0.25))
	ic.position = Vector2(7, 7)
	disc.add_child(ic)
	top.add_child(disc)
	top.add_child(UI.spacer())
	top.add_child(sw)
	col.add_child(top)
	var tl := UI.label(title, 16, UI.TEXT, "bold")
	col.add_child(tl)
	var sl := UI.label(sub, 12, UI.TEXT_DIM, "medium")
	sl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	sl.clip_text = true
	col.add_child(sl)
	b.set_meta("sub", sl)
	return b


func _update_rings(on: bool, s: Dictionary) -> void:
	var fps: Dictionary = s.get("fps", {}) if s.get("fps") is Dictionary else {}
	var target := float(s.get("target_fps", 0) if s.get("target_fps") != null else 0)
	var out = fps.get("output")
	var real = fps.get("real")
	var live: bool = on and bool(s.get("enabled", false)) and out != null and target > 0
	if live:
		_ring.set_ring(float(out), target, str(int(round(float(out)))), "FPS")
		_flow.text = str(int(round(float(real)))) if real != null else "—"
		_flow_x.text = ("×%.2f" % (float(out) / maxf(float(real), 1.0))).replace(".00", "").trim_suffix("0") if real != null and float(real) > 0 else ""
		_goal.text = "ЦЕЛЬ %d · ±8 %%" % int(target)
		var ok := float(out) >= target * 0.92
		_badge.text = "✓ НА ЦЕЛИ" if ok else "● ПОДСТРАИВАЕТСЯ"
		_badge.add_theme_color_override("font_color", UI.GREEN if ok else Color("ffb020"))
	else:
		_ring.set_ring(0, 1, str(int(target)) if target > 0 else "—", "ЦЕЛЬ FPS" if target > 0 else "FPS")
		_flow.text = "—"
		_flow_x.text = ""
		_goal.text = "GFG ВКЛЮЧИТСЯ С ИГРОЙ" if on else "GFG НЕ ПОДКЛЮЧЁН"
		_badge.text = ""
	var pw: Dictionary = s.get("power", {}) if s.get("power") is Dictionary else {}
	var tdp = pw.get("tdp_w")
	_pw_ring.set_ring(float(tdp) if tdp != null else 0.0, 15.0)
	_pw.text = ("%d Вт" % int(round(float(tdp)))) if tdp != null else "— Вт"
	var bat: Dictionary = s.get("battery", {}) if s.get("battery") is Dictionary else {}
	var pct = bat.get("percent")
	if pct == null:
		var b := SystemInfo.battery()
		pct = b["percent"] if b["available"] else null
	_bat_ring.set_ring(float(pct) if pct != null else 0.0, 100.0)
	_bat.text = ("%d %%" % int(pct)) if pct != null else "—"
