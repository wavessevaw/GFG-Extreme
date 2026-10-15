## Base for modal layers (Steam-style menu, Quick settings, power menu). While one is
## open it owns the controller: D-pad/stick move focus only between its own controls
## (nearest control in that direction), B closes it, and focus returns to where it was.
class_name Overlay
extends Control

var app: Node
var _prev_focus: Control
## The overlay's card and where it comes from: subclasses set them in _ready
## (side menu from the left, Quick settings from the right, power menu grows).
var sheet: Control
var sheet_from := Vector2.ZERO
var sheet_grow := false


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	z_index = 50
	visible = false
	mouse_filter = Control.MOUSE_FILTER_STOP


func open() -> void:
	_prev_focus = get_viewport().gui_get_focus_owner()
	visible = true
	_on_open()
	_focus_first.call_deferred()
	_animate_in()


func _animate_in() -> void:
	modulate.a = 0.0
	FX.to(self, "modulate:a", 1.0, FX.FAST)
	if sheet == null:
		return
	if sheet_grow:
		sheet.pivot_offset = sheet.size / 2.0
		sheet.scale = Vector2(0.94, 0.94)
		FX.to(sheet, "scale", Vector2.ONE, FX.MED, Tween.TRANS_BACK)
	elif sheet_from != Vector2.ZERO:
		var base: Vector2 = sheet.get_meta("_overlay_base") if sheet.has_meta("_overlay_base") else sheet.position
		sheet.set_meta("_overlay_base", base)
		sheet.position = base + sheet_from
		FX.to(sheet, "position", base, FX.MED + 0.04, Tween.TRANS_QUART)


func close() -> void:
	visible = false
	_on_close()
	if _prev_focus != null and is_instance_valid(_prev_focus) and _prev_focus.is_visible_in_tree():
		_prev_focus.grab_focus()


func _on_open() -> void:
	pass


func _on_close() -> void:
	pass


func _focus_first() -> void:
	var f := first_focus()
	if f != null:
		f.grab_focus()


func first_focus() -> Control:
	var all := focusables()
	return all[0] if not all.is_empty() else null


func focusables() -> Array:
	var out := []
	_collect(self, out)
	return out


static func _collect(n: Node, out: Array) -> void:
	for c in n.get_children():
		if c is Control and c.is_visible_in_tree():
			if c.focus_mode == Control.FOCUS_ALL and not (c is BaseButton and c.disabled):
				out.append(c)
			_collect(c, out)


## Returns true when the event was a direction and focus was moved (or kept) inside.
func navigate(event: InputEvent) -> bool:
	var dir := Vector2.ZERO
	if event.is_action_pressed("ui_up", true): dir = Vector2.UP
	elif event.is_action_pressed("ui_down", true): dir = Vector2.DOWN
	elif event.is_action_pressed("ui_left", true): dir = Vector2.LEFT
	elif event.is_action_pressed("ui_right", true): dir = Vector2.RIGHT
	if dir == Vector2.ZERO:
		return false
	var cur := get_viewport().gui_get_focus_owner()
	var all := focusables()
	if cur == null or not all.has(cur):
		if not all.is_empty():
			all[0].grab_focus()
		return true
	# a slider row consumes left/right itself
	if cur is GSliderRow and (dir == Vector2.LEFT or dir == Vector2.RIGHT):
		return false
	var from: Vector2 = cur.get_global_rect().get_center()
	var best: Control = null
	var best_score := INF
	for c in all:
		if c == cur:
			continue
		var d: Vector2 = c.get_global_rect().get_center() - from
		var along := d.dot(dir)
		if along <= 4.0:
			continue
		var across := absf(d.dot(Vector2(dir.y, dir.x)))
		var score := along + across * 2.5
		if score < best_score:
			best_score = score
			best = c
	if best != null:
		best.grab_focus()
	return true
