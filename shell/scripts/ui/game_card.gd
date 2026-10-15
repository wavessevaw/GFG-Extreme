## Game tile. Portrait capsule art (Steam's library_600x900, as the Deck's own
## library) so logos are never cropped; a header-only game shows its whole header
## over a blurred fill of itself; a game without art gets a composed cover (its
## colour, monogram and title) instead of a grey box. Focus lifts the tile with a
## soft red glow and a ring; it is drawn above its neighbours while it grows.
class_name GameCard
extends Button

signal chosen(game: Dictionary)
signal focused(game: Dictionary)

const RADIUS := 12
const LIFT := 1.07
const BLUR := preload("res://assets/shaders/blur.gdshader")

var game: Dictionary
var art_slot := "grid"
var _holder: Panel
var _fill: TextureRect
var _tex: TextureRect
var _cover: Control
var _ring: Panel
var _glow: Panel
var _shine: TextureRect


static func make(g: Dictionary, size_px: Vector2, slot: String = "grid") -> GameCard:
	var c := GameCard.new()
	c.game = g
	c.art_slot = slot
	c.custom_minimum_size = size_px
	return c


func _ready() -> void:
	focus_mode = Control.FOCUS_ALL
	var empty := StyleBoxEmpty.new()
	for st in ["normal", "hover", "pressed", "focus", "disabled"]:
		add_theme_stylebox_override(st, empty)
	# glow behind the art (shadow only)
	_glow = Panel.new()
	var gs := StyleBoxFlat.new()
	gs.bg_color = Color(UI.RED, 0.01)
	gs.set_corner_radius_all(RADIUS)
	gs.shadow_color = Color(UI.RED, 0.5)
	gs.shadow_size = 22
	_glow.add_theme_stylebox_override("panel", gs)
	_glow.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_glow.modulate.a = 0.0
	add_child(_glow)
	_holder = UI.rounded_art(RADIUS, Color("121217"))
	_holder.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_holder)
	_tex = _holder.get_node("Art")
	_fill = TextureRect.new()
	_fill.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_fill.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_fill.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := ShaderMaterial.new()
	mat.shader = BLUR
	_fill.material = mat
	_fill.visible = false
	_holder.add_child(_fill)
	_holder.move_child(_fill, 0)
	_cover = _make_cover()
	_holder.add_child(_cover)
	_holder.move_child(_cover, 0)
	# a faint top sheen and a bottom shade: art reads as a physical card
	_shine = TextureRect.new()
	var gt := GradientTexture2D.new()
	gt.gradient = Gradient.new()
	gt.gradient.set_color(0, Color(1, 1, 1, 0.08))
	gt.gradient.set_color(1, Color(0, 0, 0, 0.0))
	gt.gradient.add_point(0.45, Color(0, 0, 0, 0.0))
	gt.gradient.add_point(1.0, Color(0, 0, 0, 0.28))
	gt.fill_from = Vector2(0, 0)
	gt.fill_to = Vector2(0, 1)
	_shine.texture = gt
	_shine.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_shine.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_shine.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_holder.add_child(_shine)
	if not game.get("installed", true):
		var badge := UI.keycap("НЕ УСТАНОВЛЕНА")
		badge.modulate = Color(1, 1, 1, 0.92)
		badge.position = Vector2(10, 10)
		add_child(badge)
	_ring = Panel.new()
	var ring := UI.focus_box(UI.RED, RADIUS + 3)
	ring.set_border_width_all(3)
	ring.expand_margin_left = 4
	ring.expand_margin_right = 4
	ring.expand_margin_top = 4
	ring.expand_margin_bottom = 4
	_ring.add_theme_stylebox_override("panel", ring)
	_ring.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_ring.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ring.modulate.a = 0.0
	add_child(_ring)
	_load_art()
	pressed.connect(func(): chosen.emit(game))
	set_meta("fx_focus_scale", LIFT)
	FX.press(self)
	resized.connect(func(): pivot_offset = size / 2.0)
	focus_entered.connect(_on_focus)
	focus_exited.connect(_on_blur)


func _load_art() -> void:
	var art: Dictionary = game.get("art", {})
	var portrait := size_ratio() < 1.0
	var order: Array = [art_slot, "grid", "header", "hero"] if portrait else [art_slot, "header", "grid", "hero"]
	for slot in order:
		if not art.has(slot):
			continue
		var natural_portrait: bool = slot == "grid"
		Shell.load_art(art[slot], func(t):
			if not is_instance_valid(_tex):
				return
			_tex.texture = t
			_cover.visible = false
			if natural_portrait != portrait:
				# letterboxed: the whole art, centred over a blurred fill of itself
				_tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
				_fill.texture = t
				_fill.visible = true)
		break


func size_ratio() -> float:
	var s := custom_minimum_size
	return s.x / maxf(s.y, 1.0)


func _on_focus() -> void:
	z_index = 5
	FX.scale_to(self, LIFT, FX.MED)
	FX.to(_ring, "modulate:a", 1.0, FX.FAST)
	FX.to(_glow, "modulate:a", 1.0, FX.MED)
	focused.emit(game)


func _on_blur() -> void:
	z_index = 0
	FX.scale_to(self, 1.0, FX.FAST, Tween.TRANS_CUBIC)
	FX.to(_ring, "modulate:a", 0.0, FX.FAST)
	FX.to(_glow, "modulate:a", 0.0, FX.FAST)


## A composed cover for games without art: a deep two-tone gradient from the
## title's hash, a large monogram and the title set like a capsule.
func _make_cover() -> Control:
	var name_s := str(game.get("name", "?"))
	var h := float(abs(name_s.hash()) % 360) / 360.0
	var top := Color.from_hsv(h, 0.55, 0.42)
	var bottom := Color.from_hsv(fmod(h + 0.08, 1.0), 0.65, 0.12)
	var c := Control.new()
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var words := name_s.split(" ", false)
	var mono := ""
	for w in words.slice(0, 2):
		mono += w.substr(0, 1).to_upper()
	c.draw.connect(func():
		var s := c.size
		c.draw_polygon(PackedVector2Array([Vector2.ZERO, Vector2(s.x, 0), s, Vector2(0, s.y)]),
			PackedColorArray([top, top.darkened(0.25), bottom, bottom]))
		var f := UI.font("bold")
		var fs := int(minf(s.x, s.y) * 0.46)
		var ts := f.get_string_size(mono, HORIZONTAL_ALIGNMENT_LEFT, -1, fs)
		c.draw_string(f, Vector2((s.x - ts.x) / 2.0, s.y * 0.48 + fs * 0.35), mono,
			HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(1, 1, 1, 0.13)))
	var t := UI.label(name_s, 17, UI.TEXT, "bold")
	t.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	t.max_lines_visible = 3
	t.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	t.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	t.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	t.offset_left = 14
	t.offset_right = -14
	t.offset_bottom = -14
	t.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.5))
	t.add_theme_constant_override("shadow_offset_y", 2)
	c.add_child(t)
	return c
