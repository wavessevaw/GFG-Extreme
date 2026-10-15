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
	_vol.value_committed.connect(func(val): SystemInfo.set_volume_pct(val))
	v1.add_child(_vol)
	_wifi = UI.row("wifi", "Wi-Fi", "", UI.label("", 15, UI.TEXT_DIM, "medium"), 58)
	_wifi.pressed.connect(func(): close(); OS.create_process(GameRunner.steam_command(), ["steam://open/settings/internet"]))
	v1.add_child(_wifi)
	v.add_child(c1)
	v.add_child(UI.margin(UI.kicker("GFG"), 6, 10, 0, 2))
	var c2 := UI.panel(UI.CARD, 6, 14)
	var v2 := UI.vbox(2)
	c2.add_child(v2)
	_auto_sw = GSwitch.make(false)
	_auto = UI.row("gauge", "Autopilot", "Оптимальные настройки под ваше устройство", _auto_sw, 66)
	_auto.pressed.connect(_toggle_autopilot)
	v2.add_child(_auto)
	_fusion_sw = GSwitch.make(false)
	_fusion = UI.row("layers", "Frame Fusion", "Улучшает совместимость и плавность", _fusion_sw, 66)
	_fusion.pressed.connect(func():
		Shell.bridge.set_frame_fusion(not bool(Shell.bridge.status.get("frame_fusion", {}).get("setting", false)), _result))
	v2.add_child(_fusion)
	_boost_sw = GSwitch.make(false)
	_boost = UI.row("bolt", "Continuous Boost", "Поддерживает высокую частоту кадров", _boost_sw, 66)
	_boost.pressed.connect(func():
		Shell.bridge.set_continuous_boost(not bool(Shell.bridge.status.get("continuous_boost", false)), _result))
	v2.add_child(_boost)
	v.add_child(c2)
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
	for r in [_auto, _fusion, _boost]:
		r.disabled = not on
	_auto_sw.unknown = not on
	_fusion_sw.unknown = not on
	_boost_sw.unknown = not on
	var mode := str(s.get("mode", ""))
	if mode != "" and mode != "autopilot":
		_last_manual_mode = mode
	_auto_sw.on = mode == "autopilot"
	_fusion_sw.on = bool(s.get("frame_fusion", {}).get("setting", false))
	_boost_sw.on = bool(s.get("continuous_boost", false))
	var sub: Label = _auto.get_child(0).get_child(0).get_child(1).get_node("Sub")
	sub.text = "Оптимальные настройки под ваше устройство" if on else "GFG Extreme не подключён"


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
