## Row with a slider (Яркость / Громкость): focus it, then D-pad left/right changes the
## value in steps; A does nothing special. Emits value_committed after a short pause so
## the system command is not run on every step.
class_name GSliderRow
extends Button

signal value_committed(value: int)

var value := 50
var step := 5
var available := true
var _bar: Control
var _pct: Label
var _commit_left := 0.0


static func make(icon: String, title: String, initial: int) -> GSliderRow:
	var r := GSliderRow.new()
	r.value = clampi(initial, 0, 100) if initial >= 0 else 0
	r.available = initial >= 0
	r.set_meta("icon", icon)
	r.set_meta("title", title)
	return r


func _ready() -> void:
	focus_mode = Control.FOCUS_ALL
	custom_minimum_size = Vector2(0, 58)
	add_theme_stylebox_override("normal", UI.box(Color(0, 0, 0, 0), Color.TRANSPARENT, 10))
	add_theme_stylebox_override("hover", UI.box(Color(1, 1, 1, 0.04), Color.TRANSPARENT, 10))
	add_theme_stylebox_override("pressed", UI.box(Color(1, 1, 1, 0.04), Color.TRANSPARENT, 10))
	add_theme_stylebox_override("focus", UI.focus_box(UI.RED, 10))
	var m := UI.margin(UI.hbox(16), 16, 0, 16, 0)
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(m)
	var h: HBoxContainer = m.get_child(0)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.add_child(GIcon.make(get_meta("icon"), 24))
	var t := UI.label(get_meta("title"), 17, UI.TEXT, "semibold")
	t.custom_minimum_size = Vector2(130, 0)
	h.add_child(t)
	_bar = Control.new()
	_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_bar.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_bar.draw.connect(_draw_bar)
	h.add_child(_bar)
	_pct = UI.label("", 15, UI.TEXT_DIM, "medium")
	_pct.custom_minimum_size = Vector2(52, 0)
	_pct.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	h.add_child(_pct)
	_refresh()


func _draw_bar() -> void:
	var y := _bar.size.y / 2
	var w := _bar.size.x
	_bar.draw_line(Vector2(0, y), Vector2(w, y), Color(1, 1, 1, 0.16), 5, true)
	if not available:
		return
	var x := w * value / 100.0
	_bar.draw_line(Vector2(0, y), Vector2(x, y), UI.RED, 5, true)
	_bar.draw_circle(Vector2(x, y), 10, UI.TEXT)


func set_value(v: int) -> void:
	value = clampi(v, 0, 100)
	_refresh()


func _refresh() -> void:
	if _pct == null:
		return
	_pct.text = ("%d%%" % value) if available else "—"
	_bar.queue_redraw()


func _gui_input(event: InputEvent) -> void:
	if not available:
		return
	var d := 0
	if event.is_action_pressed("ui_left", true):
		d = -step
	elif event.is_action_pressed("ui_right", true):
		d = step
	if d != 0:
		set_value(value + d)
		_commit_left = 0.25
		accept_event()


func _process(delta: float) -> void:
	if _commit_left > 0:
		_commit_left -= delta
		if _commit_left <= 0:
			value_committed.emit(value)
