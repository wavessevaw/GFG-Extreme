## Vector icons drawn with Godot primitives: crisp at any scale, no icon font or
## image licence needed. Coordinates are on a 24x24 grid scaled to the control size.
class_name GIcon
extends Control

var icon := ""
var color := Color.WHITE
var stroke := 2.0


static func make(name: String, px: int = 22, c: Color = Color.WHITE) -> GIcon:
	var i := GIcon.new()
	i.icon = name
	i.color = c
	i.custom_minimum_size = Vector2(px, px)
	i.mouse_filter = Control.MOUSE_FILTER_IGNORE
	i.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return i


func set_icon(name: String, c: Variant = null) -> void:
	icon = name
	if c != null:
		color = c
	queue_redraw()


func _s() -> float:
	return min(size.x, size.y) / 24.0


func _p(x: float, y: float) -> Vector2:
	var s := _s()
	var off := (size - Vector2(24, 24) * s) / 2.0
	return off + Vector2(x, y) * s


func _line(pts: Array, closed := false) -> void:
	var v := PackedVector2Array()
	for p in pts:
		v.append(_p(p[0], p[1]))
	if closed:
		v.append(v[0])
	draw_polyline(v, color, stroke * _s(), true)


func _arc(cx: float, cy: float, r: float, a0: float, a1: float, fill := false) -> void:
	if fill:
		draw_circle(_p(cx, cy), r * _s(), color)
	else:
		draw_arc(_p(cx, cy), r * _s(), deg_to_rad(a0), deg_to_rad(a1), 32, color, stroke * _s(), true)


func _rect(x: float, y: float, w: float, h: float, fill := false) -> void:
	var r := Rect2(_p(x, y), Vector2(w, h) * _s())
	if fill:
		draw_rect(r, color)
	else:
		draw_rect(r, color, false, stroke * _s())


func _poly(pts: Array) -> void:
	var v := PackedVector2Array()
	for p in pts:
		v.append(_p(p[0], p[1]))
	draw_colored_polygon(v, color)


func _draw() -> void:
	match icon:
		"wifi":
			_arc(12, 19, 14, 225, 315); _arc(12, 19, 9.5, 225, 315); _arc(12, 19, 5, 225, 315); _arc(12, 18.5, 1.6, 0, 360, true)
		"battery":
			_rect(2, 7, 18, 10); _rect(20.5, 10, 1.8, 4, true)
		"home":
			_line([[3, 11], [12, 3.5], [21, 11]]); _line([[5.5, 9.5], [5.5, 20], [18.5, 20], [18.5, 9.5]]); _rect(10, 14, 4, 6, true)
		"library":
			_rect(4, 4, 3.4, 16, true); _rect(9.2, 4, 3.4, 16, true); _poly([[14.5, 5.2], [17.6, 4.2], [21.6, 19], [18.5, 20]])
		"store":
			_line([[2, 4], [5, 4], [7.5, 15.5], [19, 15.5], [21, 7.5], [6, 7.5]]); _arc(9, 19.5, 1.7, 0, 360, true); _arc(17.5, 19.5, 1.7, 0, 360, true)
		"friends":
			_arc(9, 8, 3.2, 0, 360, true); _poly([[3, 20], [3.5, 15.5], [6, 13], [12, 13], [14.5, 15.5], [15, 20]])
			_arc(17, 8.5, 2.6, 0, 360, true); _poly([[16, 13], [19.5, 13], [21.5, 15.5], [21.8, 20], [16.6, 20], [16.4, 15.5]])
		"download":
			_line([[12, 3], [12, 15]]); _line([[7, 10.5], [12, 15.5], [17, 10.5]]); _line([[4, 20.5], [20, 20.5]])
		"settings", "gear":
			_arc(12, 12, 3.2, 0, 360)
			for k in 8:
				var a := deg_to_rad(k * 45.0)
				var p1 := Vector2(12, 12) + Vector2(cos(a), sin(a)) * 6.0
				var p2 := Vector2(12, 12) + Vector2(cos(a), sin(a)) * 9.2
				_line([[p1.x, p1.y], [p2.x, p2.y]])
			_arc(12, 12, 6.6, 0, 360)
		"power":
			_arc(12, 13, 8, -55, 235); _line([[12, 2.5], [12, 12]])
		"search":
			_arc(10.5, 10.5, 6.5, 0, 360); _line([[15.3, 15.3], [21, 21]])
		"play":
			_poly([[7, 4.5], [19.5, 12], [7, 19.5]])
		"clock":
			_arc(12, 12, 9, 0, 360); _line([[12, 6.5], [12, 12], [16, 14]])
		"cloud":
			_arc(8, 14, 4.5, 0, 360, true); _arc(13.5, 11, 5.5, 0, 360, true); _arc(17.5, 15, 3.8, 0, 360, true); _rect(8, 14, 9.5, 4.8, true)
		"trophy":
			_poly([[6.5, 3.5], [17.5, 3.5], [17, 10], [12, 14], [7, 10]]); _line([[6.5, 5.5], [3, 5.5], [3.5, 8.5], [7, 10]]); _line([[17.5, 5.5], [21, 5.5], [20.5, 8.5], [17, 10]])
			_rect(11, 14, 2, 3.5, true); _rect(7.5, 17.5, 9, 2.5, true)
		"sun":
			_arc(12, 12, 4, 0, 360, true)
			for k in 8:
				var a2 := deg_to_rad(k * 45.0)
				var q1 := Vector2(12, 12) + Vector2(cos(a2), sin(a2)) * 7.0
				var q2 := Vector2(12, 12) + Vector2(cos(a2), sin(a2)) * 9.5
				_line([[q1.x, q1.y], [q2.x, q2.y]])
		"volume":
			_poly([[3, 9], [7, 9], [12, 4.5], [12, 19.5], [7, 15], [3, 15]]); _arc(13, 12, 4.5, -50, 50); _arc(13, 12, 8, -50, 50)
		"moon":
			_arc(12, 12, 8.5, 0, 360, true)
			draw_circle(_p(16.5, 8.5), 7.0 * _s(), get_meta("bg", Color("15151a")))
		"monitor", "display":
			_rect(3, 4, 18, 12.5); _line([[12, 16.5], [12, 20]]); _line([[8, 20.5], [16, 20.5]])
		"gamepad", "controller":
			_poly([[6, 7], [18, 7], [21.5, 16], [19.5, 19], [16, 16.5], [8, 16.5], [4.5, 19], [2.5, 16]])
			var keep := color
			color = get_meta("bg", Color("15151a"))
			_line([[7, 10], [7, 14]]); _line([[5, 12], [9, 12]]); _arc(16.5, 10.5, 1.1, 0, 360, true); _arc(18.5, 13, 1.1, 0, 360, true)
			color = keep
		"storage":
			_rect(3, 5, 18, 14); _line([[3, 13], [21, 13]]); _arc(17, 16, 1.2, 0, 360, true)
		"brush":
			_line([[20, 4], [10.5, 13.5]]); _poly([[10, 13], [12, 15], [9, 20], [4, 20.5], [5.5, 16.5]])
		"close":
			_line([[6, 6], [18, 18]]); _line([[18, 6], [6, 18]])
		"backspace":
			_line([[8, 5], [21, 5], [21, 19], [8, 19], [2.5, 12]], true); _line([[11, 9], [17, 15]]); _line([[17, 9], [11, 15]])
		"shift":
			_line([[12, 3.5], [21, 12.5], [16, 12.5], [16, 20], [8, 20], [8, 12.5], [3, 12.5]], true)
		"keyboard":
			_rect(2, 6, 20, 12)
			for xk in [5, 9, 13, 17]:
				_rect(xk, 9, 2, 2, true)
			_rect(7, 13.5, 10, 1.8, true)
		"chevron":
			_line([[9, 5], [16, 12], [9, 19]])
		"chevron_down":
			_line([[5, 9], [12, 16], [19, 9]])
		"dots":
			for xd in [5, 12, 19]:
				_arc(xd, 12, 1.9, 0, 360, true)
		"dots_v":
			for yd in [5, 12, 19]:
				_arc(12, yd, 1.9, 0, 360, true)
		"bolt":
			_poly([[13.5, 2], [5, 13.5], [11, 13.5], [10, 22], [19, 10], [13, 10]])
		"layers":
			_line([[12, 3], [21.5, 8], [12, 13], [2.5, 8]], true); _line([[2.5, 12], [12, 17], [21.5, 12]]); _line([[2.5, 16], [12, 21], [21.5, 16]])
		"gauge", "autopilot":
			_arc(12, 13, 8.5, 150, 390); _line([[12, 13], [16.5, 8.5]]); _arc(12, 13, 1.6, 0, 360, true)
		"user":
			_arc(12, 8, 4, 0, 360, true); _poly([[4, 21], [5, 15.5], [8, 13.5], [16, 13.5], [19, 15.5], [20, 21]])
		"star":
			var pts := []
			for k in 10:
				var a3 := deg_to_rad(-90 + k * 36.0)
				var r := 9.5 if k % 2 == 0 else 4.0
				pts.append([12 + cos(a3) * r, 12.5 + sin(a3) * r])
			_poly(pts)
		"info":
			_arc(12, 12, 9, 0, 360); _line([[12, 11], [12, 17]]); _arc(12, 7.6, 1.2, 0, 360, true)
		"refresh":
			_arc(12, 12, 8, 30, 320); _poly([[20.5, 4.5], [21, 11], [14.5, 9.5]])
		"pause":
			_rect(7, 5, 3.5, 14, true); _rect(13.5, 5, 3.5, 14, true)
		"sleep":
			_arc(12, 12, 8.5, 0, 360)
			_line([[9, 9], [15, 9], [9, 15], [15, 15]])
		"globe", "internet":
			_arc(12, 12, 9, 0, 360); _line([[3, 12], [21, 12]]); _arc(12, 12, 4.5, -90, 90); _arc(12, 12, 4.5, 90, 270)
		_:
			_arc(12, 12, 3, 0, 360, true)
