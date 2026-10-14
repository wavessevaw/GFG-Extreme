## Game tile as in the mockups: artwork with rounded corners, a red 3 px ring when
## focused (no zoom, so neighbours and overlays are never covered), the title on a
## dark placeholder when Steam has no cached art.
class_name GameCard
extends Button

signal chosen(game: Dictionary)
signal focused(game: Dictionary)

const RADIUS := 10

var game: Dictionary
var art_slot := "header"
var _tex: TextureRect
var _title: Label
var _ring: Panel


static func make(g: Dictionary, size_px: Vector2, slot: String = "header") -> GameCard:
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
	var holder := UI.rounded_art(RADIUS)
	holder.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(holder)
	_tex = holder.get_node("Art")
	_title = UI.label(str(game.get("name", "")), 18, UI.TEXT_DIM, "semibold")
	_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_title.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 14)
	holder.add_child(_title)
	holder.move_child(_title, 0)
	if not game.get("installed", true):
		var badge := UI.keycap("НЕ УСТАНОВЛЕНА")
		badge.position = Vector2(10, 10)
		add_child(badge)
	_ring = Panel.new()
	var ring := UI.focus_box(UI.RED, RADIUS + 2)
	ring.expand_margin_left = 3
	ring.expand_margin_right = 3
	ring.expand_margin_top = 3
	ring.expand_margin_bottom = 3
	_ring.add_theme_stylebox_override("panel", ring)
	_ring.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_ring.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ring.visible = false
	add_child(_ring)
	var art: Dictionary = game.get("art", {})
	var order := [art_slot, "header", "grid", "hero"]
	for slot in order:
		if art.has(slot):
			Shell.load_art(art[slot], func(t):
				if is_instance_valid(_tex):
					_tex.texture = t
					_title.visible = false)
			break
	pressed.connect(func(): chosen.emit(game))
	focus_entered.connect(func(): _ring.visible = true; focused.emit(game))
	focus_exited.connect(func(): _ring.visible = false)
