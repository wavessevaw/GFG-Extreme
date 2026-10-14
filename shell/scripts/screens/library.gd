## Библиотека (mockup 02): title + count, segmented filter (Все / Установлено /
## Избранное / Не Steam) and search, a 4-column grid of art tiles with the red ring.
extends Screen

const FILTERS := [["all", "Все"], ["installed", "Установлено"], ["favorites", "Избранное"], ["nonsteam", "Не Steam"]]
const COLS := 4

var _seg: HBoxContainer
var _grid: GridContainer
var _count: Label
var _search: Button
var _scroll: ScrollContainer
var _filter := "all"


func _ready() -> void:
	title = "Библиотека"
	_filter = str(Shell.settings.get("filter", "all"))
	if not FILTERS.any(func(f): return f[0] == _filter):
		_filter = "all"
	var v := UI.vbox(18)
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 52
	v.offset_right = -52
	v.offset_top = 16
	add_child(v)
	var bar := UI.hbox(16)
	v.add_child(bar)
	bar.add_child(UI.label("Библиотека", 40, UI.TEXT, "bold"))
	_count = UI.label("", 18, UI.TEXT_DIM, "medium")
	_count.size_flags_vertical = Control.SIZE_SHRINK_END
	bar.add_child(UI.margin(_count, 0, 0, 0, 8))
	bar.add_child(UI.spacer())
	var segp := UI.panel(Color(0.08, 0.08, 0.1, 0.9), 4, 14)
	segp.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_seg = UI.hbox(4)
	segp.add_child(_seg)
	for f in FILTERS:
		var b := Button.new()
		b.text = f[1]
		b.focus_mode = Control.FOCUS_ALL
		b.custom_minimum_size = Vector2(124, 42)
		b.add_theme_font_override("font", UI.font("semibold"))
		b.add_theme_font_size_override("font_size", 16)
		b.add_theme_stylebox_override("focus", UI.focus_box(UI.TEXT, 11))
		b.set_meta("filter", f[0])
		b.pressed.connect(_set_filter.bind(f[0]))
		_seg.add_child(b)
	bar.add_child(segp)
	_search = UI.icon_button("search", 50)
	_search.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_search.pressed.connect(func(): app.push("search"))
	bar.add_child(_search)
	_scroll = ScrollContainer.new()
	_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	_scroll.follow_focus = true
	v.add_child(_scroll)
	_grid = GridContainer.new()
	_grid.columns = COLS
	_grid.add_theme_constant_override("h_separation", 18)
	_grid.add_theme_constant_override("v_separation", 18)
	_scroll.add_child(UI.margin(_grid, 4, 4, 4, 24))
	Shell.library_changed.connect(_rebuild)
	Shell.favorites_changed.connect(func(): if _filter == "favorites": _rebuild())
	_rebuild()


func hints() -> Array:
	return [["A", "Выбрать"], ["B", "Назад"], ["Y", "Избранное"], ["X", "Поиск"]]


func option() -> bool:
	var f := get_viewport().gui_get_focus_owner()
	if f is GameCard:
		Shell.toggle_favorite(f.game)
		app.toast(("★ В избранном: " if Shell.is_favorite(f.game) else "Убрано из избранного: ") + f.game.name)
		return true
	return false


func _set_filter(f: String) -> void:
	_filter = f
	Shell.set_setting("filter", f)
	_rebuild()


func _rebuild() -> void:
	for b in _seg.get_children():
		var on: bool = b.get_meta("filter") == _filter
		var sb := UI.box(UI.RED if on else Color(0, 0, 0, 0), Color.TRANSPARENT, 11, 14)
		for st in ["normal", "hover", "pressed"]:
			b.add_theme_stylebox_override(st, sb)
		b.add_theme_color_override("font_color", UI.TEXT if on else UI.TEXT_DIM)
	for c in _grid.get_children():
		_grid.remove_child(c)
		c.queue_free()
	var list := Shell.filtered_games(_filter, str(Shell.settings.get("sort", "name")))
	_count.text = "%d игр" % list.size()
	for g in list:
		var c := GameCard.make(g, Vector2(282, 214), "header")
		c.chosen.connect(app.open_game)
		_grid.add_child(c)
	if list.is_empty():
		_grid.add_child(UI.label("Здесь пока пусто", 18, UI.TEXT_DIM))


func focus_default() -> void:
	await get_tree().process_frame
	if _grid.get_child_count() > 0 and _grid.get_child(0) is Button:
		_grid.get_child(0).grab_focus()
	else:
		_seg.get_child(0).grab_focus()
