## Быстрые настройки (View button), two tabs switched with L1 / R1:
##   GFG     — the plugin's rings (FPS with the wolf, power, battery), mode tiles, the Auto
##             priority, "GFG in this game" and six feature switches.
##   Система — brightness, volume, Wi-Fi, battery, sleep and the power menu.
## Every GFG control is one Governor setting through the Bridge; the shell itself never
## changes power limits.
class_name QuickSettings
extends Overlay

const WOLF := preload("res://assets/gfg_wolf.png")
const MODES := [["budget", "Battery", "battery"], ["balanced", "Balanced", "gauge"],
	["quality", "Quality", "star"], ["autopilot", "Auto", ""]]
const PREFS := [["auto", "Баланс"], ["battery", "Батарея"], ["smoothness", "Плавность"]]
## [key in status, icon, title, subtitle]; each one is a Governor feature switch.
const FEATURES := [["frame_fusion", "layers", "Frame Fusion", "Плавнее кадры"],
	["boost", "bolt", "Boost", "Тяжёлые сцены"],
	["touch_boost", "gamepad", "Boost стиком", "При движении"],
	["continuous_boost", "refresh", "Continuous", "Всегда · больше Вт"],
	["latency", "clock", "Тайминг кадров", "Ровнее подача"],
	["hud", "monitor", "Кольца в игре", "HUD поверх игры"]]

var tab := ""                    # "gfg" | "sys"; empty until first open
var _tabs := {}                  # name -> Button
var _pages := {}                 # name -> Control
var _status: Label
var _clock: Label
# Система
var _bright: GSliderRow
var _vol: GSliderRow
var _wifi: Button
var _bat_big: GRing
var _bat_time: Label
var _bat_sub: Label
# GFG
var _hero: Button
var _ring: GRing
var _flow: Label
var _flow_x: Label
var _goal: Label
var _badge: Label
var _state: Label
var _pw_ring: GRing
var _pw: Label
var _bat_ring: GRing
var _bat: Label
var _enabled_sw: GSwitch
var _enabled_row: Button
var _modes: HBoxContainer
var _prefs: HBoxContainer
var _feat := {}                  # key -> [Button, GSwitch]
var _off_note: Label


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
	var v := UI.vbox(12)
	p.add_child(UI.margin(v, 4, 8, 4, 10))
	var head := UI.hbox(14)
	head.add_child(UI.label("Быстрые настройки", 26, UI.TEXT, "bold"))
	head.add_child(UI.spacer())
	_status = UI.label("", 16, UI.TEXT, "semibold")
	head.add_child(_status)
	_clock = UI.label("", 17, UI.TEXT, "bold")
	head.add_child(_clock)
	v.add_child(head)
	v.add_child(_tab_bar())
	var sys := _build_sys()
	var gfg := _build_gfg()
	v.add_child(sys)
	v.add_child(gfg)
	_pages = {"sys": sys, "gfg": gfg}
	Shell.bridge.status_updated.connect(func(_s): if visible: _refresh_gfg())
	Shell.bridge.connection_changed.connect(func(_c): if visible: _refresh_gfg())


# --- tabs -------------------------------------------------------------------------

func _tab_bar() -> Control:
	var bar := UI.panel(Color(0, 0, 0, 0.35), 4, 12)
	var h := UI.hbox(6)
	bar.add_child(h)
	h.add_child(_vcenter(UI.keycap("L1")))
	for t in [["sys", "Система"], ["gfg", "GFG"]]:
		var b := Button.new()
		b.focus_mode = Control.FOCUS_NONE   # L1 / R1 switch tabs; the D-pad stays on content
		b.custom_minimum_size = Vector2(0, 42)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var row := UI.hbox(8)
		row.alignment = BoxContainer.ALIGNMENT_CENTER
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		if t[0] == "gfg":
			row.add_child(_wolf(22))
		var l := UI.label(t[1], 16, UI.TEXT, "semibold")
		l.name = "Name"
		row.add_child(l)
		b.add_child(row)
		b.pressed.connect(show_tab.bind(t[0]))
		_tabs[t[0]] = b
		h.add_child(b)
	h.add_child(_vcenter(UI.keycap("R1")))
	return bar


func on_tab(_dir: int) -> void:
	show_tab("gfg" if tab == "sys" else "sys")


func show_tab(name: String) -> void:
	tab = name
	for k in _pages:
		_pages[k].visible = k == name
	for k in _tabs:
		var on: bool = k == name
		var sb := UI.box(UI.RED if on else Color(0, 0, 0, 0), Color.TRANSPARENT, 9)
		for st in ["normal", "hover", "pressed"]:
			_tabs[k].add_theme_stylebox_override(st, sb)
		(_tabs[k].get_child(0).get_node("Name") as Label).add_theme_color_override(
			"font_color", UI.TEXT if on else UI.TEXT_DIM)
	if visible:
		_focus_first()   # now: the focused control may have just been hidden


# --- Система ----------------------------------------------------------------------

func _build_sys() -> Control:
	var v := UI.vbox(10)
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
	var c2 := UI.panel(UI.CARD, 16, 14)
	var bh := UI.hbox(18)
	c2.add_child(bh)
	_bat_big = GRing.make(68, 7, UI.GREEN)
	_bat_big.text_size = 17
	bh.add_child(_bat_big)
	var bv := UI.vbox(2)
	bv.alignment = BoxContainer.ALIGNMENT_CENTER
	bv.add_child(_small("БАТАРЕЯ"))
	_bat_time = UI.label("", 21, UI.TEXT, "bold")
	bv.add_child(_bat_time)
	_bat_sub = UI.label("", 13, UI.TEXT_DIM, "medium")
	bv.add_child(_bat_sub)
	bh.add_child(bv)
	v.add_child(c2)
	var c3 := UI.panel(UI.CARD, 6, 14)
	var v3 := UI.vbox(2)
	c3.add_child(v3)
	var sleep := UI.row("sleep", "Сон", "", GIcon.make("chevron", 18, UI.TEXT_DIM), 58)
	sleep.pressed.connect(func(): close(); SystemInfo.power("suspend"))
	v3.add_child(sleep)
	var pwr := UI.row("power", "Питание", "", GIcon.make("chevron", 18, UI.TEXT_DIM), 58)
	pwr.pressed.connect(func(): close(); app._power.open())
	v3.add_child(pwr)
	v.add_child(c3)
	return v


# --- GFG --------------------------------------------------------------------------

func _build_gfg() -> Control:
	var v := UI.vbox(8)
	# hero: A opens the GFG page with every detail
	_hero = Button.new()
	_hero.focus_mode = Control.FOCUS_ALL
	_hero.custom_minimum_size = Vector2(0, 146)
	_hero.add_theme_stylebox_override("normal", UI.box(UI.CARD, UI.LINE, 14))
	_hero.add_theme_stylebox_override("hover", UI.box(UI.CARD.lightened(0.03), UI.LINE, 14))
	_hero.add_theme_stylebox_override("pressed", UI.box(UI.CARD, UI.LINE, 14))
	_hero.add_theme_stylebox_override("focus", UI.focus_box(UI.TEXT, 14))
	_hero.pressed.connect(func(): close(); app.push("gfg"))
	var hh := UI.hbox(16)
	hh.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var hm := UI.margin(hh, 14, 12, 14, 12)
	hm.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hm.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hero.add_child(hm)
	_ring = GRing.make(118, 9, UI.RED)
	_ring.wolf = true
	_ring.text_size = 34
	_ring.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hh.add_child(_ring)
	var hv := UI.vbox(2)
	hv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hv.alignment = BoxContainer.ALIGNMENT_CENTER
	hv.mouse_filter = Control.MOUSE_FILTER_IGNORE
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
	_state = UI.label("", 13, UI.TEXT_DIM, "medium")
	hv.add_child(_state)
	hh.add_child(hv)
	var minis := UI.vbox(8)
	minis.alignment = BoxContainer.ALIGNMENT_CENTER
	minis.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var more := UI.label("A — подробно ›", 12, UI.TEXT_DIM, "semibold")
	more.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	minis.add_child(more)
	var m1 := _mini("bolt", Color("ff8a3d"))
	_pw_ring = m1[0]
	_pw = m1[1]
	minis.add_child(m1[2])
	var m2 := _mini("battery", UI.GREEN)
	_bat_ring = m2[0]
	_bat = m2[1]
	minis.add_child(m2[2])
	hh.add_child(minis)
	v.add_child(_hero)
	# mode + "GFG in this game"
	var sec := UI.hbox(8)
	sec.add_child(_vcenter(_small("РЕЖИМ")))
	sec.add_child(UI.spacer())
	_enabled_sw = GSwitch.make(true)
	_enabled_row = Button.new()
	_enabled_row.focus_mode = Control.FOCUS_ALL
	_enabled_row.custom_minimum_size = Vector2(250, 34)
	var clear := UI.box(Color(0, 0, 0, 0), Color.TRANSPARENT, 9)
	for st in ["normal", "pressed", "disabled"]:
		_enabled_row.add_theme_stylebox_override(st, clear)
	_enabled_row.add_theme_stylebox_override("hover", UI.box(Color(1, 1, 1, 0.04), Color.TRANSPARENT, 9))
	_enabled_row.add_theme_stylebox_override("focus", UI.focus_box(UI.RED, 9))
	var er := UI.hbox(10)
	er.alignment = BoxContainer.ALIGNMENT_END
	er.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var erm := UI.margin(er, 8, 0, 6, 0)
	erm.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	erm.mouse_filter = Control.MOUSE_FILTER_IGNORE
	er.add_child(_vcenter(_small("GFG В ЭТОЙ ИГРЕ")))
	_enabled_sw.mouse_filter = Control.MOUSE_FILTER_IGNORE
	er.add_child(_vcenter(_enabled_sw))
	_enabled_row.add_child(erm)
	_enabled_row.pressed.connect(func():
		Shell.bridge.set_enabled(not bool(Shell.bridge.status.get("enabled", false)), _result))
	sec.add_child(_enabled_row)
	v.add_child(sec)
	_modes = UI.hbox(8)
	for m in MODES:
		_modes.add_child(_mode_tile(m))
	v.add_child(_modes)
	var pp := UI.panel(Color(0, 0, 0, 0.35), 3, 10)
	_prefs = UI.hbox(4)
	pp.add_child(_prefs)
	for pr in PREFS:
		var b := Button.new()
		b.text = pr[1]
		b.focus_mode = Control.FOCUS_ALL
		b.custom_minimum_size = Vector2(0, 34)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_override("font", UI.font("semibold"))
		b.add_theme_font_size_override("font_size", 14)
		b.add_theme_stylebox_override("focus", UI.focus_box(UI.TEXT, 8))
		b.set_meta("pref", pr[0])
		b.pressed.connect(func(): Shell.bridge.set_preference(pr[0], _result))
		_prefs.add_child(b)
	v.add_child(pp)
	v.add_child(UI.margin(_small("КАДРЫ И УСКОРЕНИЕ"), 2, 4, 0, 0))
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 8)
	grid.add_theme_constant_override("v_separation", 8)
	for f in FEATURES:
		var sw := GSwitch.make(false)
		var t := _tile(f[1], f[2], f[3], sw)
		t.pressed.connect(_toggle_feature.bind(f[0]))
		_feat[f[0]] = [t, sw]
		grid.add_child(t)
	v.add_child(grid)
	_off_note = UI.label("", 13, UI.TEXT_DIM, "medium")
	_off_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	v.add_child(_off_note)
	return v


func _mode_tile(m: Array) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.custom_minimum_size = Vector2(0, 64)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.add_theme_stylebox_override("focus", UI.focus_box(UI.TEXT, 12))
	b.set_meta("mode", m[0])
	b.set_meta("icon", m[2])
	b.pressed.connect(func(): Shell.bridge.set_mode(m[0], _result))
	var col := UI.vbox(4)
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var ic: Control = _wolf(22) if m[2] == "" else GIcon.make(m[2], 20, UI.TEXT_DIM)
	ic.name = "Icon"
	ic.custom_minimum_size = Vector2(22, 22)
	ic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
	col.add_child(ic)
	var l := UI.label(m[1], 14, UI.TEXT_DIM, "semibold")
	l.name = "Name"
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(l)
	b.add_child(col)
	return b


func _toggle_feature(key: String) -> void:
	var now: bool = _feature_on(Shell.bridge.status, key)
	match key:
		"frame_fusion":
			Shell.bridge.set_frame_fusion(not now, _result)
		"hud":
			Shell.bridge.set_hud(not now, _result)
		_:
			Shell.bridge.set_feature(key, not now, _result)


static func _feature_on(s: Dictionary, key: String) -> bool:
	if key == "frame_fusion":
		var ff: Variant = s.get("frame_fusion", {})
		return ff is Dictionary and bool(ff.get("setting", false))
	# boost, touch_boost and latency are on unless switched off; the rest off unless on
	return bool(s.get(key, key in ["boost", "touch_boost", "latency"]))


# --- refresh ----------------------------------------------------------------------

func _on_open() -> void:
	if tab == "":
		tab = "gfg" if Shell.bridge.connected else "sys"
	show_tab(tab)
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
	_status.text = ("%d %%" % b.percent) if b.available else ""
	_clock.text = Time.get_time_string_from_system().substr(0, 5)
	_refresh_gfg()


func first_focus() -> Control:
	if tab == "gfg" and _hero.is_visible_in_tree():
		return _hero
	return super.first_focus()


func _refresh_gfg() -> void:
	var on := Shell.bridge.connected
	var s := Shell.bridge.status
	var enabled: bool = on and bool(s.get("enabled", false))
	var mode := str(s.get("mode", "")) if on else ""
	_enabled_row.disabled = not on
	_enabled_sw.unknown = not on
	_enabled_sw.on = enabled
	for b in _modes.get_children():
		b.disabled = not enabled
		b.modulate.a = 1.0 if enabled else 0.45
		var active: bool = enabled and b.get_meta("mode") == mode
		var sb := UI.box(Color(UI.RED, 0.20) if active else Color(1, 1, 1, 0.035),
			UI.RED if active else Color(1, 1, 1, 0.07), 12)
		sb.set_border_width_all(2 if active else 1)
		for st in ["normal", "pressed", "disabled"]:
			b.add_theme_stylebox_override(st, sb)
		b.add_theme_stylebox_override("hover", sb if active else UI.box(Color(1, 1, 1, 0.06), Color(1, 1, 1, 0.1), 12))
		(b.get_child(0).get_node("Name") as Label).add_theme_color_override("font_color", UI.TEXT if active else UI.TEXT_DIM)
		var ic = b.get_child(0).get_node("Icon")
		if ic is GIcon:
			ic.set_icon(b.get_meta("icon"), UI.RED.lightened(0.25) if active else UI.TEXT_DIM)
	# the Auto priority only means something in Auto
	_prefs.get_parent().visible = enabled and mode == "autopilot"
	var pref := str(s.get("preference", "auto"))
	for b in _prefs.get_children():
		var act: bool = b.get_meta("pref") == pref
		var sb := UI.box(Color(1, 1, 1, 0.12) if act else Color(0, 0, 0, 0), Color.TRANSPARENT, 8, 8)
		for st in ["normal", "hover", "pressed", "disabled"]:
			b.add_theme_stylebox_override(st, sb)
		b.add_theme_color_override("font_color", UI.TEXT if act else UI.TEXT_DIM)
		b.add_theme_color_override("font_hover_color", UI.TEXT)
		b.add_theme_color_override("font_focus_color", UI.TEXT if act else UI.TEXT_DIM)
	for key in _feat:
		var t: Button = _feat[key][0]
		var sw: GSwitch = _feat[key][1]
		t.disabled = not enabled
		t.modulate.a = 1.0 if enabled else 0.45
		sw.unknown = not on
		sw.on = _feature_on(s, key)
	if not on:
		_off_note.text = "GFG Extreme не подключён: запустите Steam с плагином GFG Extreme (Decky)."
	elif not enabled:
		_off_note.text = "GFG выключен для этой игры — игра идёт как обычно."
	else:
		_off_note.text = ""
	_off_note.visible = _off_note.text != ""
	_update_rings(on, s)
	_update_battery(s)


func _result(ok: bool, r: Dictionary) -> void:
	if not ok or r.get("success") == false:
		app.toast("GFG: %s" % str(r.get("error", "ошибка")))
	Shell.bridge.call_method("status", {}, func(ok2, st):
		if ok2:
			Shell.bridge.status = st
			Shell.bridge.status_updated.emit(st))


func _update_rings(on: bool, s: Dictionary) -> void:
	var fps: Dictionary = s.get("fps", {}) if s.get("fps") is Dictionary else {}
	var target := float(s.get("target_fps", 0) if s.get("target_fps") != null else 0)
	var out = fps.get("output")
	var real = fps.get("real")
	var live: bool = on and bool(s.get("enabled", false)) and out != null and target > 0
	var pw: Dictionary = s.get("power", {}) if s.get("power") is Dictionary else {}
	var tdp = pw.get("tdp_w")
	var temp = _temp(s)
	if live:
		_ring.set_ring(float(out), target, str(int(round(float(out)))), "FPS")
		_flow.text = str(int(round(float(real)))) if real != null else "—"
		_flow_x.text = _mult(float(out), float(real)) if real != null and float(real) > 0 else ""
		_goal.text = "ЦЕЛЬ %d · ±8 %%" % int(target)
		var ok := float(out) >= target * 0.92
		_badge.text = "✓ НА ЦЕЛИ" if ok else "● ПОДСТРАИВАЕТСЯ"
		_badge.add_theme_color_override("font_color", UI.GREEN if ok else Color("ffb020"))
		var bits := []
		if tdp != null:
			bits.append("Лимит %d Вт" % int(round(float(tdp))))
		if temp != null:
			bits.append("%d °C" % int(round(float(temp))))
		_state.text = " · ".join(bits)
	else:
		_ring.set_ring(0, 1, str(int(target)) if target > 0 else "—", "ЦЕЛЬ FPS" if target > 0 else "FPS")
		_flow.text = "—"
		_flow_x.text = ""
		_goal.text = "GFG ВКЛЮЧИТСЯ С ИГРОЙ" if on else "GFG НЕ ПОДКЛЮЧЁН"
		_badge.text = ""
		_state.text = ""
	_pw_ring.set_ring(float(tdp) if tdp != null else 0.0, 15.0)
	_pw.text = ("%d Вт" % int(round(float(tdp)))) if tdp != null else "— Вт"


static func _temp(s: Dictionary) -> Variant:
	var sensors: Variant = s.get("sensors")
	return sensors.get("temp_c") if sensors is Dictionary else null


## 84 / 28 -> "×3", 60 / 27 -> "×2.22"
static func _mult(out: float, real: float) -> String:
	var m := out / maxf(real, 1.0)
	if absf(m - round(m)) < 0.05:
		return "×%d" % int(round(m))
	return ("×%.2f" % m).rstrip("0")


func _update_battery(s: Dictionary) -> void:
	var bat: Dictionary = s.get("battery", {}) if s.get("battery") is Dictionary else {}
	var pct = bat.get("percent")
	var charging := bool(bat.get("charging", false))
	if pct == null:
		var b := SystemInfo.battery()
		pct = b["percent"] if b["available"] else null
		charging = bool(b.get("charging", false))
	var mins = bat.get("minutes_left")
	var left := ("%d:%02d" % [int(mins) / 60, int(mins) % 60]) if mins != null else ""
	_bat_ring.set_ring(float(pct) if pct != null else 0.0, 100.0)
	_bat.text = left if left != "" else (("%d %%" % int(pct)) if pct != null else "—")
	_bat_big.set_ring(float(pct) if pct != null else 0.0, 100.0, ("%d%%" % int(pct)) if pct != null else "—", "")
	if charging:
		_bat_time.text = "Заряжается"
	elif mins != null:
		_bat_time.text = "≈ %d ч %02d мин" % [int(mins) / 60, int(mins) % 60]
	else:
		_bat_time.text = ("%d %%" % int(pct)) if pct != null else "Нет данных"
	var pw: Dictionary = s.get("power", {}) if s.get("power") is Dictionary else {}
	var parts := []
	if pw.get("draw_w") != null:
		parts.append("Потребление %.1f Вт" % float(pw.get("draw_w")))
	var temp = _temp(s)
	if temp != null:
		parts.append("%d °C" % int(round(float(temp))))
	_bat_sub.text = " · ".join(parts)


# --- small builders ---------------------------------------------------------------

func _small(t: String) -> Label:
	var l := UI.label(t, 12, UI.TEXT_DIM, "bold")
	l.add_theme_font_override("font", UI.tracked("bold", 2))
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _wolf(px: int) -> TextureRect:
	var w := TextureRect.new()
	w.texture = WOLF
	w.custom_minimum_size = Vector2(px, px)
	w.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	w.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	w.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return w


func _vcenter(c: Control) -> Control:
	c.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return c


## A small ring with an icon, and its value beside it.
func _mini(icon: String, col: Color) -> Array:
	var h := UI.hbox(8)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var r := GRing.make(38, 5, col)
	r.icon = icon
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var holder := Control.new()
	holder.custom_minimum_size = Vector2(38, 38)
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(r)
	r.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var ic := GIcon.make(icon, 14, col)
	ic.custom_minimum_size = Vector2(14, 14)
	ic.size = Vector2(14, 14)
	ic.position = Vector2(12, 12)
	holder.add_child(ic)
	h.add_child(holder)
	var l := UI.label("—", 15, UI.TEXT, "bold")
	l.custom_minimum_size = Vector2(56, 0)
	h.add_child(l)
	return [r, l, h]


## A switch tile: icon disc and switch on top, title and one line under them.
func _tile(icon: String, title: String, sub: String, sw: GSwitch) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.custom_minimum_size = Vector2(0, 80)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var sb := UI.box(Color(1, 1, 1, 0.035), Color(1, 1, 1, 0.07), 12)
	for st in ["normal", "pressed", "disabled"]:
		b.add_theme_stylebox_override(st, sb)
	b.add_theme_stylebox_override("hover", UI.box(Color(1, 1, 1, 0.06), Color(1, 1, 1, 0.09), 12))
	b.add_theme_stylebox_override("focus", UI.focus_box(UI.RED, 12))
	var col := UI.vbox(2)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var m := UI.margin(col, 11, 10, 11, 8)
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(m)
	var top := UI.hbox(6)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var disc := Panel.new()
	disc.custom_minimum_size = Vector2(26, 26)
	disc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	disc.add_theme_stylebox_override("panel", UI.box(Color(UI.RED, 0.16), Color.TRANSPARENT, 8))
	var ic := GIcon.make(icon, 14, UI.RED.lightened(0.25))
	ic.position = Vector2(6, 6)
	disc.add_child(ic)
	top.add_child(disc)
	top.add_child(UI.spacer())
	sw.mouse_filter = Control.MOUSE_FILTER_IGNORE
	top.add_child(sw)
	col.add_child(top)
	col.add_child(UI.spacer(false))
	var tl := UI.label(title, 14, UI.TEXT, "bold")
	tl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	tl.clip_text = true
	col.add_child(tl)
	var sl := UI.label(sub, 11, UI.TEXT_DIM, "medium")
	sl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	sl.clip_text = true
	col.add_child(sl)
	return b
