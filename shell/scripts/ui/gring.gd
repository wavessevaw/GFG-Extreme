## The GFG ring (same as the plugin's): a track, an arc for value/max with a soft glow, and in the
## middle an optional wolf, a big number and a small caption. Small rings carry an icon instead.
class_name GRing
extends Control

const WOLF := preload("res://assets/gfg_wolf.png")

var value := 0.0:
	set(v):
		value = v
		queue_redraw()
var max_value := 1.0:
	set(v):
		max_value = v
		queue_redraw()
var color := UI.RED
var thickness := 10.0
var text := ""
var caption := ""
var text_size := 40
var wolf := false
var icon := ""
var _shown := 0.0


static func make(px: int, thick: float, col: Color) -> GRing:
	var r := GRing.new()
	r.custom_minimum_size = Vector2(px, px)
	r.thickness = thick
	r.color = col
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return r


func set_ring(v: float, m: float, t: String = "", cap: String = "") -> void:
	value = v
	max_value = m
	text = t
	caption = cap
	queue_redraw()


func _process(delta: float) -> void:
	var f := clampf(value / maxf(max_value, 1e-6), 0.0, 1.0)
	if absf(_shown - f) > 0.002:
		_shown = lerpf(_shown, f, minf(1.0, delta * 6.0))   # the arc eases to the new value
		queue_redraw()


func _draw() -> void:
	var c := size / 2.0
	var r := minf(size.x, size.y) / 2.0 - thickness / 2.0 - 2.0
	draw_arc(c, r, 0, TAU, 96, Color(1, 1, 1, 0.08), thickness, true)
	if _shown > 0.003:
		var a0 := -PI / 2.0
		var a1 := a0 + TAU * _shown
		if thickness >= 8.0:   # glow under the main ring only
			draw_arc(c, r, a0, a1, 96, Color(color, 0.18), thickness + 8.0, true)
		draw_arc(c, r, a0, a1, 96, color, thickness, true)
	var f := UI.font("bold")
	var y := c.y
	if wolf:
		var ws := size.x * 0.22
		draw_texture_rect(WOLF, Rect2(c.x - ws / 2.0, c.y - ws - text_size * 0.28, ws, ws), false)
		y = c.y + text_size * 0.42
	else:
		y = c.y + text_size * 0.34 - (6 if caption != "" else 0)
	if icon != "" and text == "":
		return
	if text != "":
		var ts := f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, text_size)
		draw_string(f, Vector2(c.x - ts.x / 2.0, y), text, HORIZONTAL_ALIGNMENT_LEFT, -1, text_size, UI.TEXT)
	if caption != "":
		var cf := UI.font("semibold")
		var cs := maxi(10, int(text_size * 0.26))
		var w := cf.get_string_size(caption, HORIZONTAL_ALIGNMENT_LEFT, -1, cs)
		draw_string(cf, Vector2(c.x - w.x / 2.0, y + cs + 6), caption, HORIZONTAL_ALIGNMENT_LEFT, -1, cs, UI.TEXT_DIM)
