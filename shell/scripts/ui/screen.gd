## Base for every page. The app calls enter() when the page is shown, focus_default()
## to place controller focus, back() on B and option() on Y (return true when handled),
## and hints() for the glyph bar.
class_name Screen
extends Control

var app: Node   # scripts/app.gd
var title := ""


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	size_flags_vertical = Control.SIZE_EXPAND_FILL


func enter(_args: Dictionary = {}) -> void:
	pass


func focus_default() -> void:
	var c := _first_focusable(self)
	if c != null:
		c.grab_focus()


func back() -> bool:
	return false


func option() -> bool:
	return false


func hints() -> Array:
	return [["A", "Выбрать"], ["B", "Назад"], ["X", "Поиск"]]


static func _first_focusable(n: Node) -> Control:
	for ch in n.get_children():
		if ch is Control and ch.visible:
			if ch.focus_mode == Control.FOCUS_ALL:
				return ch
			var r := _first_focusable(ch)
			if r != null:
				return r
	return null


## Horizontal scrolling row of cards; keeps the focused card visible.
static func card_row(cards: Array, height: int, sep: int = 16) -> ScrollContainer:
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(0, height)
	sc.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	sc.follow_focus = true
	var row := UI.hbox(sep)
	sc.add_child(UI.margin(row, 4, 4, 4, 4))
	for c in cards:
		row.add_child(c)
	return sc
