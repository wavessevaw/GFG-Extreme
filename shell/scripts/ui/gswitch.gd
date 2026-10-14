## On/off pill switch as in the mockups (red when on). Display only: the row that
## holds it is the focusable control.
class_name GSwitch
extends Control

var on := false:
	set(v):
		on = v
		queue_redraw()
var unknown := false:
	set(v):
		unknown = v
		queue_redraw()


static func make(value: bool) -> GSwitch:
	var s := GSwitch.new()
	s.on = value
	s.custom_minimum_size = Vector2(52, 30)
	s.mouse_filter = Control.MOUSE_FILTER_IGNORE
	s.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return s


func _draw() -> void:
	var h := size.y
	var track := Rect2(Vector2.ZERO, size)
	var sb := StyleBoxFlat.new()
	sb.set_corner_radius_all(int(h / 2))
	sb.bg_color = UI.RED if (on and not unknown) else Color(1, 1, 1, 0.14)
	draw_style_box(sb, track)
	var r := h / 2 - 4
	var x := size.x - h / 2 if (on and not unknown) else h / 2
	draw_circle(Vector2(x, h / 2), r, Color(1, 1, 1, 0.95 if not unknown else 0.4))
