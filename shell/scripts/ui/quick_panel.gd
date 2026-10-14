## Быстрые настройки: right-side panel (View button). Autopilot mode, Frame Fusion,
## Continuous Boost, live FPS/temperature, volume, power. Over a running game this needs
## the stage-D overlay path; in the shell itself it works now.
class_name QuickPanel
extends Control

var app: Node
var _panel: PanelContainer
var _stats: Label
var _vol: Label
var _controls: GfgControls
var _prev_focus: Control


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	visible = false
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.5)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	_panel = UI.panel(UI.BG2, 22)
	_panel.set_anchors_and_offsets_preset(Control.PRESET_RIGHT_WIDE)
	_panel.offset_left = -420
	add_child(_panel)
	var v := UI.vbox(14)
	_panel.add_child(v)
	v.add_child(UI.label("Быстрые настройки", 24, UI.TEXT, true))
	_stats = UI.label("", 16, UI.TEXT_DIM)
	v.add_child(_stats)
	_controls = GfgControls.make(true, func(t): app.toast(t))
	v.add_child(_controls)
	_vol = UI.label("", 16)
	v.add_child(_vol)
	var vh := UI.hbox(8)
	for step in [-10, 10]:
		var b := UI.button("Звук %s" % ("−" if step < 0 else "+"), false, 0, 48)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.pressed.connect(func(): SystemInfo.change_volume(step); _refresh())
		vh.add_child(b)
	v.add_child(vh)
	var pw := UI.button("Питание", false, 0, 48)
	pw.pressed.connect(func(): close(); app.show_power_menu())
	v.add_child(pw)
	var cl := UI.button("Закрыть", false, 0, 48)
	cl.pressed.connect(close)
	v.add_child(cl)
	Shell.bridge.status_updated.connect(func(_s): if visible: _refresh())


func open() -> void:
	_prev_focus = get_viewport().gui_get_focus_owner()
	visible = true
	_refresh()
	var f := Screen._first_focusable(_controls)
	if f:
		f.grab_focus.call_deferred()
	Log.info("ui", "quick panel open")


func close() -> void:
	visible = false
	if _prev_focus != null and is_instance_valid(_prev_focus) and _prev_focus.is_visible_in_tree():
		_prev_focus.grab_focus()


func _refresh() -> void:
	var s := Shell.bridge.status if Shell.bridge.connected else {}
	var fps = s.get("fps", {}).get("output")
	var t = s.get("sensors", {}).get("temp_c")
	var b := SystemInfo.battery()
	_stats.text = "FPS %s   ·   %s   ·   батарея %s" % [str(int(fps)) if fps != null else "—",
		("%d°C" % int(t)) if t != null else "—°C", ("%d%%" % b.percent) if b.available else "—"]
	var vp := SystemInfo.volume_pct()
	_vol.text = "Громкость: " + (("%d%%" % vp) if vp >= 0 else "—")
