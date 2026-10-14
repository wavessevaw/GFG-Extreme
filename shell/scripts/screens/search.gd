## Поиск: own on-screen keyboard + live results (name prefix first, then substring).
extends Screen

var _query: Label
var _results: VBoxContainer
var _osk: Osk


func _ready() -> void:
	title = "Поиск"
	var h := UI.hbox(24)
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(UI.margin(h, 32, 12, 32, 12))
	get_child(0).set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var left := UI.vbox(14)
	h.add_child(left)
	var qp := UI.panel(UI.CARD, 16)
	_query = UI.label("Введите название игры", 24, UI.TEXT_DIM)
	_query.custom_minimum_size = Vector2(660, 0)
	qp.add_child(_query)
	left.add_child(qp)
	_osk = Osk.new()
	_osk.text_changed.connect(_on_text)
	_osk.submitted.connect(func(_t): if _results.get_child_count() > 0 and _results.get_child(0) is Button: _results.get_child(0).grab_focus())
	left.add_child(_osk)
	var sc := ScrollContainer.new()
	sc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	h.add_child(sc)
	_results = UI.vbox(8)
	_results.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(_results)


func _on_text(t: String) -> void:
	_query.text = t if t != "" else "Введите название игры"
	_query.add_theme_color_override("font_color", UI.TEXT if t != "" else UI.TEXT_DIM)
	for c in _results.get_children():
		c.queue_free()
	var found := Shell.search(t)
	for g in found.slice(0, 30):
		var b := UI.button(g.name + ("" if g.installed else "   · не установлена"), false, 0, 50)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.pressed.connect(app.open_game.bind(g))
		_results.add_child(b)
	if t != "" and found.is_empty():
		_results.add_child(UI.label("Ничего не найдено", 18, UI.TEXT_DIM))


func focus_default() -> void:
	_osk.focus_first()
