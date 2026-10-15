## Загрузки (mockup 06): the update Steam is running (progress from the app manifest),
## the queue of games with a pending update, and free space. Steam does the downloading;
## pause/resume open Steam's own downloads page.
extends Screen

var _v: VBoxContainer


func _ready() -> void:
	title = "Загрузки"
	var sc := ScrollContainer.new()
	sc.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	sc.offset_left = 52
	sc.offset_right = -52
	sc.offset_top = 10
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	sc.follow_focus = true
	add_child(sc)
	_v = UI.vbox(14)
	_v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var m := UI.margin(_v, 0, 0, 0, 20)
	m.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(m)


func hints() -> Array:
	return [["A", "Выбрать"], ["B", "Назад"]]


func enter(_args: Dictionary = {}) -> void:
	Shell.reload_library()
	for c in _v.get_children():
		_v.remove_child(c)
		c.queue_free()
	_v.add_child(UI.label("Загрузки", 40, UI.TEXT, "bold"))
	var pending := Shell.games.filter(func(g): return g.get("update_pending", false))
	pending.sort_custom(func(a, b): return int(a.get("downloading", false)) > int(b.get("downloading", false)))
	if pending.is_empty():
		var p := UI.panel(UI.CARD, 22, 14)
		p.add_child(UI.label("Нет активных загрузок и обновлений", 19, UI.TEXT_DIM, "medium"))
		_v.add_child(p)
	else:
		_v.add_child(_item(pending[0], true))
		if pending.size() > 1:
			_v.add_child(UI.label("В очереди (%d)" % (pending.size() - 1), 20, UI.TEXT, "bold"))
			for g in pending.slice(1):
				_v.add_child(_item(g, false))
	_v.add_child(_storage())
	var open := UI.button("Открыть загрузки Steam", false, 340, 54, "download")
	open.pressed.connect(func(): OS.create_process(GameRunner.steam_command(), ["steam://open/downloads"]))
	_v.add_child(open)


func _item(g: Dictionary, big: bool) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.custom_minimum_size = Vector2(0, 150 if big else 92)
	b.add_theme_stylebox_override("normal", UI.box(UI.CARD, UI.LINE, 12))
	b.add_theme_stylebox_override("hover", UI.box(UI.CARD_HI, UI.LINE, 12))
	b.add_theme_stylebox_override("focus", UI.focus_box(UI.RED, 12))
	b.pressed.connect(app.open_game.bind(g))
	var h := UI.hbox(22)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var m := UI.margin(h, 10, 10, 22, 10)
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(m)
	var thumb := UI.rounded_art(8)
	thumb.custom_minimum_size = Vector2(280 if big else 180, 0)
	var art: Dictionary = g.get("art", {})
	if art.has("header"):
		Shell.load_art(art.header, func(t): (thumb.get_node("Art") as TextureRect).texture = t)
	h.add_child(thumb)
	var v := UI.vbox(6)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_child(UI.label(("Обновление" if g.get("installed", false) else "Установка") if big else g.name, 22 if big else 18, UI.TEXT, "bold"))
	var total := int(g.get("bytes_to_download", 0))
	var done := int(g.get("bytes_downloaded", 0))
	var frac := clampf(float(done) / total, 0.0, 1.0) if total > 0 else 0.0
	var sub := "%s / %s" % [UI.fmt_size(done), UI.fmt_size(total)] if total > 0 else "ожидает обновления"
	v.add_child(UI.label((g.name + "  ·  " + sub) if big else sub, 15, UI.TEXT_DIM, "medium"))
	var bar := Control.new()
	bar.custom_minimum_size = Vector2(0, 12)
	bar.draw.connect(func():
		var y := bar.size.y / 2
		bar.draw_line(Vector2(0, y), Vector2(bar.size.x, y), Color(1, 1, 1, 0.14), 6, true)
		if frac > 0:
			bar.draw_line(Vector2(0, y), Vector2(bar.size.x * frac, y), UI.RED, 6, true))
	v.add_child(bar)
	h.add_child(v)
	var pct := UI.label("%d%%" % int(frac * 100), 18, UI.TEXT, "semibold")
	pct.custom_minimum_size = Vector2(60, 0)
	pct.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	h.add_child(pct)
	h.add_child(GIcon.make("pause" if g.get("downloading", false) else "dots_v", 26, UI.TEXT))
	return b


func _storage() -> Control:
	var p := UI.panel(UI.CARD, 18, 12)
	var h := UI.hbox(18)
	p.add_child(h)
	h.add_child(GIcon.make("cloud", 24))
	var st := SystemInfo.storage(Shell.library.steam_root) if Shell.library.steam_root != "" else {}
	h.add_child(UI.label(("SSD %s" % UI.fmt_size(st.total)) if not st.is_empty() else "Хранилище", 17, UI.TEXT, "semibold"))
	var used: float = 1.0 - float(st.get("free", 0)) / max(1.0, float(st.get("total", 1)))
	var bar := Control.new()
	bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.custom_minimum_size = Vector2(0, 20)
	bar.draw.connect(func():
		var y := bar.size.y / 2
		bar.draw_line(Vector2(0, y), Vector2(bar.size.x, y), Color(1, 1, 1, 0.14), 10, true)
		bar.draw_line(Vector2(0, y), Vector2(bar.size.x * used, y), UI.RED, 10, true))
	h.add_child(bar)
	h.add_child(UI.label(("Свободно " + UI.fmt_size(st.free)) if not st.is_empty() else "—", 16, UI.TEXT_DIM, "medium"))
	return p
