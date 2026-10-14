## Библиотека: filters Все / Установлено / Избранное / Недавние / Не Steam, sort, portrait grid.
extends Screen

const FILTERS := [["all", "Все"], ["installed", "Установлено"], ["favorites", "Избранное"], ["recent", "Недавние"], ["nonsteam", "Не Steam"]]
const COLS := 6

var _chips: HBoxContainer
var _grid: GridContainer
var _count: Label
var _sort_btn: Button
var _filter := "all"
var _sort := "name"


func _ready() -> void:
	title = "Библиотека"
	_filter = str(Shell.settings.get("filter", "all"))
	_sort = str(Shell.settings.get("sort", "name"))
	var v := UI.vbox(14)
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(UI.margin(v, 32, 12, 32, 12))
	get_child(0).set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bar := UI.hbox(10)
	v.add_child(bar)
	_chips = UI.hbox(10)
	bar.add_child(_chips)
	for f in FILTERS:
		var b := UI.button(f[1], false, 0, 42)
		b.toggle_mode = true
		b.set_meta("filter", f[0])
		b.pressed.connect(_set_filter.bind(f[0]))
		_chips.add_child(b)
	bar.add_child(UI.spacer())
	_count = UI.label("", 16, UI.TEXT_DIM)
	bar.add_child(_count)
	_sort_btn = UI.button("", false, 190, 42)
	_sort_btn.pressed.connect(func():
		_sort = "recent" if _sort == "name" else "name"
		Shell.set_setting("sort", _sort)
		_rebuild())
	bar.add_child(_sort_btn)
	var sc := ScrollContainer.new()
	sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	v.add_child(sc)
	_grid = GridContainer.new()
	_grid.columns = COLS
	_grid.add_theme_constant_override("h_separation", 18)
	_grid.add_theme_constant_override("v_separation", 18)
	sc.add_child(UI.margin(_grid, 8, 8, 8, 8))
	Shell.library_changed.connect(_rebuild)
	Shell.favorites_changed.connect(func(): if _filter == "favorites": _rebuild())
	_rebuild()


func enter(args: Dictionary = {}) -> void:
	if args.has("filter"):
		_set_filter(args.filter)


func _set_filter(f: String) -> void:
	_filter = f
	Shell.set_setting("filter", f)
	_rebuild()


func _rebuild() -> void:
	for b in _chips.get_children():
		b.button_pressed = b.get_meta("filter") == _filter
		b.add_theme_stylebox_override("normal", UI.box(UI.RED if b.button_pressed else UI.CARD))
	_sort_btn.text = "Сортировка: " + ("имя" if _sort == "name" else "недавние")
	for c in _grid.get_children():
		c.queue_free()
	var list := Shell.filtered_games(_filter, _sort)
	_count.text = "%d игр" % list.size()
	for g in list:
		var c := GameCard.make(g, Vector2(172, 258), "grid")
		c.chosen.connect(app.open_game)
		_grid.add_child(c)
	if list.is_empty():
		_grid.add_child(UI.label("Здесь пока пусто", 18, UI.TEXT_DIM))


func focus_default() -> void:
	await get_tree().process_frame
	if _grid.get_child_count() > 0 and _grid.get_child(0) is Button:
		_grid.get_child(0).grab_focus()
	else:
		_chips.get_child(0).grab_focus()
