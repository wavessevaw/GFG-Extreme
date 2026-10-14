## Поиск (mockup 08): search field with clear, live results, own on-screen keyboard.
## Prefix matches first, then substring; Cyrillic and Latin both work.
extends Screen

var _field: Label
var _clear: Button
var _results: VBoxContainer
var _osk: Osk


func _ready() -> void:
	title = "Поиск"
	var v := UI.vbox(14)
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 52
	v.offset_right = -52
	v.offset_top = 10
	v.offset_bottom = -16
	add_child(v)
	var fp := UI.panel(UI.CARD, 18, 14)
	fp.custom_minimum_size = Vector2(0, 62)
	var fh := UI.hbox(14)
	fp.add_child(fh)
	fh.add_child(GIcon.make("search", 24, UI.TEXT_DIM))
	_field = UI.label("", 22, UI.TEXT, "medium")
	_field.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	fh.add_child(_field)
	_clear = UI.icon_button("close", 40)
	_clear.pressed.connect(func(): _osk.clear(); _osk.focus_first())
	fh.add_child(_clear)
	v.add_child(fp)
	var sc := ScrollContainer.new()
	sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	sc.follow_focus = true
	_results = UI.vbox(6)
	_results.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(_results)
	v.add_child(sc)
	_osk = Osk.new()
	_osk.text_changed.connect(_on_text)
	_osk.submitted.connect(func(_t): _focus_results())
	_osk.hide_requested.connect(_focus_results)
	v.add_child(_osk)
	_on_text("")


func hints() -> Array:
	return [["A", "Ввести"], ["B", "Назад"], ["Y", "Стереть"]]


func option() -> bool:
	_osk._backspace()
	return true


func _focus_results() -> void:
	if _results.get_child_count() > 0 and _results.get_child(0) is Button:
		_results.get_child(0).grab_focus()


func _on_text(t: String) -> void:
	_field.text = t + "|" if t != "" else "Название игры"
	_field.add_theme_color_override("font_color", UI.TEXT if t != "" else UI.MUTED)
	for c in _results.get_children():
		_results.remove_child(c)
		c.queue_free()
	var found := Shell.search(t) if t != "" else Shell.recent_games(4)
	for g in found.slice(0, 12):
		_results.add_child(_result_row(g))
	if t != "" and found.is_empty():
		_results.add_child(UI.label("Ничего не найдено", 18, UI.TEXT_DIM))


func _result_row(g: Dictionary) -> Button:
	var b := UI.row("", g.name, ("Не установлена" if not g.installed else ("Не Steam" if g.kind == "shortcut" else "Steam")), null, 66)
	var thumb := UI.rounded_art(6)
	thumb.custom_minimum_size = Vector2(112, 52)
	thumb.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var h: HBoxContainer = b.get_child(0).get_child(0)
	h.add_child(thumb)
	h.move_child(thumb, 0)
	var art: Dictionary = g.get("art", {})
	var path: String = art.get("header", art.get("grid", ""))
	if path != "":
		Shell.load_art(path, func(t): (thumb.get_node("Art") as TextureRect).texture = t)
	b.pressed.connect(app.open_game.bind(g))
	return b


func focus_default() -> void:
	_osk.focus_first()
