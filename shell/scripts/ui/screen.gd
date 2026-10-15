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


## Horizontal scrolling row of cards; keeps the focused card visible. The scroll
## area reaches PAD past the column on every side so a lifted, glowing card is not
## clipped, while the cards stay aligned with the text above them.
const ROW_PAD := 18


static func card_row(cards: Array, height: int, sep: int = 16) -> Control:
	var wrap := Control.new()
	wrap.custom_minimum_size = Vector2(0, height)
	wrap.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sc := ScrollContainer.new()
	sc.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	sc.offset_left = -ROW_PAD
	sc.offset_right = ROW_PAD
	sc.offset_top = -ROW_PAD
	sc.offset_bottom = ROW_PAD
	sc.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	sc.follow_focus = true
	var row := UI.hbox(sep)
	sc.add_child(UI.margin(row, ROW_PAD, ROW_PAD, ROW_PAD, ROW_PAD))
	for c in cards:
		row.add_child(c)
	wrap.add_child(sc)
	return wrap
