## Autopilot mode selector + Frame Fusion + Continuous Boost toggles, shared by the
## GFG Center page and the Quick panel. Every press is one Governor setting via the Bridge.
class_name GfgControls
extends VBoxContainer

const MODES := [["budget", "Батарея"], ["balanced", "Баланс"], ["quality", "Качество"], ["autopilot", "Autopilot"]]

var compact := false
var _modes: GridContainer
var _fusion: Button
var _boost: Button
var _note: Label
var _toast: Callable


static func make(compact_layout: bool, toast: Callable) -> GfgControls:
	var c := GfgControls.new()
	c.compact = compact_layout
	c._toast = toast
	return c


func _ready() -> void:
	add_theme_constant_override("separation", 10)
	add_child(UI.label("Режим GFG", 15, UI.TEXT_DIM))
	_modes = GridContainer.new()
	_modes.columns = 2 if compact else 4
	_modes.add_theme_constant_override("h_separation", 8)
	_modes.add_theme_constant_override("v_separation", 8)
	add_child(_modes)
	for m in MODES:
		var b := UI.button(m[1], false, 150 if compact else 150, 50)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.set_meta("mode", m[0])
		b.pressed.connect(func(): Shell.bridge.set_mode(m[0], _result))
		_modes.add_child(b)
	_fusion = UI.toggle("Frame Fusion", null)
	_fusion.pressed.connect(func():
		var cur: bool = Shell.bridge.status.get("frame_fusion", {}).get("setting", false)
		Shell.bridge.set_frame_fusion(not cur, _result))
	add_child(_fusion)
	_boost = UI.toggle("Continuous Boost", null)
	_boost.pressed.connect(func():
		var cur: bool = Shell.bridge.status.get("continuous_boost", false)
		Shell.bridge.set_continuous_boost(not cur, _result))
	add_child(_boost)
	_note = UI.label("", 13, UI.TEXT_DIM)
	_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(_note)
	Shell.bridge.status_updated.connect(func(_s): refresh())
	Shell.bridge.connection_changed.connect(func(_c): refresh())
	refresh()


func _result(ok: bool, r: Dictionary) -> void:
	if not ok and _toast.is_valid():
		_toast.call("GFG: %s" % r.get("error", "ошибка"))
	Shell.bridge.call_method("status", {}, func(ok2, s): if ok2: Shell.bridge.status = s; Shell.bridge.status_updated.emit(s))


func refresh() -> void:
	var on := Shell.bridge.connected
	var s := Shell.bridge.status
	for b in _modes.get_children():
		b.disabled = not on
		var active: bool = on and b.get_meta("mode") == str(s.get("mode", ""))
		b.add_theme_stylebox_override("normal", UI.box(UI.RED if active else UI.CARD_HI))
	_fusion.disabled = not on
	_boost.disabled = not on
	UI.set_toggle(_fusion, s.get("frame_fusion", {}).get("setting") if on else null)
	UI.set_toggle(_boost, s.get("continuous_boost") if on else null)
	if not on:
		_note.text = "GFG Extreme не подключён (%s)." % Shell.bridge.last_error
	else:
		var ff := str(s.get("frame_fusion", {}).get("state", ""))
		_note.text = "Frame Fusion работает только в Autopilot; изменения — со следующего запуска игры.%s" % ((" Состояние: " + ff) if ff != "" else "")
