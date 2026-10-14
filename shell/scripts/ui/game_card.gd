## A focusable game capsule: portrait (library grid) or landscape (home rows) artwork,
## with the title drawn on a placeholder when Steam has no cached art.
class_name GameCard
extends Button

signal chosen(game: Dictionary)

var game: Dictionary
var art_slot := "grid"
var _tex: TextureRect
var _title: Label
var _badge: Label
var _ring: Panel


static func make(g: Dictionary, size_px: Vector2, slot: String = "grid") -> GameCard:
	var c := GameCard.new()
	c.game = g
	c.art_slot = slot
	c.custom_minimum_size = size_px
	return c


func _ready() -> void:
	focus_mode = Control.FOCUS_ALL
	clip_contents = true
	add_theme_stylebox_override("normal", UI.box(UI.CARD, Color.TRANSPARENT, 8, 0))
	add_theme_stylebox_override("hover", UI.box(UI.CARD_HI, Color.TRANSPARENT, 8, 0))
	add_theme_stylebox_override("pressed", UI.box(UI.CARD_HI, Color.TRANSPARENT, 8, 0))
	add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	_title = UI.label(str(game.get("name", "")), 16, UI.TEXT_DIM)
	_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_title.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 10)
	_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_title)
	_tex = TextureRect.new()
	_tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_tex.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_tex.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_tex)
	if not game.get("installed", true):
		_badge = UI.label("не установлена", 13, UI.TEXT_DIM)
		_badge.add_theme_stylebox_override("normal", UI.box(Color(0, 0, 0, 0.7), Color.TRANSPARENT, 6, 6))
		_badge.position = Vector2(6, 6)
		add_child(_badge)
	# Focus ring drawn above the artwork (a Button's own focus box sits under its children).
	_ring = Panel.new()
	var ring := UI.focus_box()
	ring.expand_margin_left = 0
	ring.expand_margin_right = 0
	ring.expand_margin_top = 0
	ring.expand_margin_bottom = 0
	ring.set_corner_radius_all(8)
	_ring.add_theme_stylebox_override("panel", ring)
	_ring.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_ring.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ring.visible = false
	add_child(_ring)
	var art: Dictionary = game.get("art", {})
	var path: String = art.get(art_slot, art.get("header", art.get("grid", "")))
	if path != "":
		Shell.load_art(path, func(t): if is_instance_valid(_tex): _tex.texture = t; _title.visible = false)
	pressed.connect(func(): chosen.emit(game))
	focus_entered.connect(_on_focus.bind(true))
	focus_exited.connect(_on_focus.bind(false))
	resized.connect(func(): pivot_offset = size / 2.0)


func _on_focus(on: bool) -> void:
	var tw := create_tween()
	tw.tween_property(self, "scale", Vector2(1.06, 1.06) if on else Vector2.ONE, 0.12)
	z_index = 1 if on else 0
	_ring.visible = on
