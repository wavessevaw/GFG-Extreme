## Центр GFG Extreme: live telemetry (FPS, CPU, GPU, temp, TDP) and the Governor settings.
## Read-only for power: TDP/GPU clocks belong to the Governor.
extends Screen

const MODES := [["budget", "Battery"], ["balanced", "Balanced"], ["quality", "Quality"], ["autopilot", "Autopilot"]]

var _tiles := {}
var _state: Label
var _seg: HBoxContainer
var _fusion: Button
var _boost: Button
var _fusion_sw: GSwitch
var _boost_sw: GSwitch


func _ready() -> void:
	title = "GFG Extreme"
	var v := UI.vbox(16)
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 52
	v.offset_right = -52
	v.offset_top = 10
	add_child(v)
	var head := UI.hbox(14)
	head.add_child(UI.label("GFG Extreme", 40, UI.TEXT, "bold"))
	_state = UI.label("", 16, UI.TEXT_DIM, "medium")
	_state.size_flags_vertical = Control.SIZE_SHRINK_END
	head.add_child(UI.margin(_state, 0, 0, 0, 8))
	v.add_child(head)
	var tiles := UI.hbox(14)
	v.add_child(tiles)
	for t in [["fps", "FPS", "monitor"], ["real", "Реальные", "layers"], ["cpu", "CPU", "settings"], ["gpu", "GPU", "bolt"], ["temp", "Температура", "sun"], ["tdp", "TDP", "power"]]:
		var p := UI.panel(UI.CARD, 16, 14)
		p.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var pv := UI.vbox(4)
		p.add_child(pv)
		var hh := UI.hbox(8)
		hh.add_child(GIcon.make(t[2], 18, UI.TEXT_DIM))
		hh.add_child(UI.label(t[1], 14, UI.TEXT_DIM, "semibold"))
		pv.add_child(hh)
		var val := UI.label("—", 32, UI.TEXT, "bold")
		pv.add_child(val)
		_tiles[t[0]] = val
		tiles.add_child(p)
	var segp := UI.panel(UI.CARD, 6, 14)
	_seg = UI.hbox(6)
	segp.add_child(_seg)
	for m in MODES:
		var b := Button.new()
		b.text = m[1]
		b.focus_mode = Control.FOCUS_ALL
		b.custom_minimum_size = Vector2(0, 54)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_override("font", UI.font("semibold"))
		b.add_theme_font_size_override("font_size", 18)
		b.add_theme_stylebox_override("focus", UI.focus_box(UI.TEXT, 10))
		b.set_meta("mode", m[0])
		b.pressed.connect(func(): Shell.bridge.set_mode(m[0], _result))
		_seg.add_child(b)
	v.add_child(segp)
	var c := UI.panel(UI.CARD, 6, 14)
	var cv := UI.vbox(2)
	c.add_child(cv)
	_fusion_sw = GSwitch.make(false)
	_fusion = UI.row("layers", "Frame Fusion", "Работает в Autopilot; применяется со следующего запуска игры", _fusion_sw, 66)
	_fusion.pressed.connect(func(): Shell.bridge.set_frame_fusion(not bool(Shell.bridge.status.get("frame_fusion", {}).get("setting", false)), _result))
	cv.add_child(_fusion)
	_boost_sw = GSwitch.make(false)
	_boost = UI.row("bolt", "Continuous Boost", "Поддерживает высокую частоту кадров", _boost_sw, 66)
	_boost.pressed.connect(func(): Shell.bridge.set_continuous_boost(not bool(Shell.bridge.status.get("continuous_boost", false)), _result))
	cv.add_child(_boost)
	v.add_child(c)
	Shell.bridge.status_updated.connect(func(_s): _refresh())
	Shell.bridge.connection_changed.connect(func(_c): _refresh())
	_refresh()


func _result(ok: bool, r: Dictionary) -> void:
	if not ok:
		app.toast("GFG: %s" % r.get("error", "ошибка"))
	Shell.bridge.call_method("status", {}, func(ok2, st):
		if ok2:
			Shell.bridge.status = st
			Shell.bridge.status_updated.emit(st))


func _fmt(v: Variant, suffix: String, digits: int = 0) -> String:
	if v == null:
		return "—"
	return (("%." + str(digits) + "f") % float(v)) + suffix


func _refresh() -> void:
	var on := Shell.bridge.connected
	var s := Shell.bridge.status if on else {}
	_tiles.fps.text = _fmt(s.get("fps", {}).get("output"), "")
	_tiles.real.text = _fmt(s.get("fps", {}).get("real"), "")
	_tiles.cpu.text = _fmt(s.get("sensors", {}).get("cpu_pct"), "%")
	_tiles.gpu.text = _fmt(s.get("sensors", {}).get("gpu_busy_pct"), "%")
	_tiles.temp.text = _fmt(s.get("sensors", {}).get("temp_c"), "°")
	_tiles.tdp.text = _fmt(s.get("power", {}).get("tdp_w"), " Вт", 1)
	var mode := str(s.get("mode", ""))
	for b in _seg.get_children():
		b.disabled = not on
		var active: bool = on and b.get_meta("mode") == mode
		var sb := UI.box(UI.RED if active else Color(0, 0, 0, 0), Color.TRANSPARENT, 10, 12)
		for st in ["normal", "hover", "pressed", "disabled"]:
			b.add_theme_stylebox_override(st, sb)
		b.add_theme_color_override("font_color", UI.TEXT if active else UI.TEXT_DIM)
	_fusion.disabled = not on
	_boost.disabled = not on
	_fusion_sw.unknown = not on
	_boost_sw.unknown = not on
	_fusion_sw.on = bool(s.get("frame_fusion", {}).get("setting", false))
	_boost_sw.on = bool(s.get("continuous_boost", false))
	_state.text = ("Governor: %s · %s" % [str(s.get("state", "—")), UI.mode_name(mode)]) if on \
		else "не подключён — нужен плагин GFG Extreme с GFG Bridge"


func focus_default() -> void:
	_seg.get_child(0).grab_focus()
