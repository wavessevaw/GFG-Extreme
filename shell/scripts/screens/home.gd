## Главная: "Продолжить игру" hero, Недавно играли, Избранное, GFG Autopilot card.
extends Screen

var _hero_btn: Button
var _hero_tex: TextureRect
var _hero_title: Label
var _hero_sub: Label
var _hero_game: Dictionary = {}
var _rows: VBoxContainer
var _gfg: Label


func _ready() -> void:
	title = "Главная"
	var sc := ScrollContainer.new()
	sc.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	add_child(sc)
	var v := UI.vbox(18)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var m := UI.margin(v, 32, 12, 32, 24)
	m.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(m)

	var hero := Control.new()
	hero.custom_minimum_size = Vector2(0, 300)
	hero.clip_contents = true
	v.add_child(hero)
	var bg := Panel.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.add_theme_stylebox_override("panel", UI.box(UI.CARD, Color.TRANSPARENT, 14, 0))
	hero.add_child(bg)
	_hero_tex = TextureRect.new()
	_hero_tex.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_hero_tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_hero_tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	hero.add_child(_hero_tex)
	var shade := ColorRect.new()
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.color = Color(0, 0, 0, 0.35)
	hero.add_child(shade)
	var info := UI.vbox(6)
	info.alignment = BoxContainer.ALIGNMENT_END
	info.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	info.offset_left = 32
	info.offset_bottom = -28
	hero.add_child(info)
	info.add_child(UI.label("ПРОДОЛЖИТЬ ИГРУ", 15, UI.RED, true))
	_hero_title = UI.label("", 34, UI.TEXT, true)
	info.add_child(_hero_title)
	_hero_sub = UI.label("", 16, UI.TEXT_DIM)
	info.add_child(_hero_sub)
	_hero_btn = UI.button("▶  Играть", true, 200, 52)
	_hero_btn.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_hero_btn.pressed.connect(func(): if not _hero_game.is_empty(): app.open_game(_hero_game))
	info.add_child(_hero_btn)

	_rows = UI.vbox(14)
	v.add_child(_rows)
	var card := UI.panel(UI.CARD, 18)
	var ch := UI.hbox(16)
	card.add_child(ch)
	ch.add_child(UI.label("GFG AUTOPILOT", 15, UI.RED, true))
	_gfg = UI.label("", 17, UI.TEXT)
	ch.add_child(_gfg)
	ch.add_child(UI.spacer())
	var open := UI.button("Центр GFG", false, 180, 44)
	open.pressed.connect(func(): app.go_tab("gfg"))
	ch.add_child(open)
	v.add_child(card)

	Shell.library_changed.connect(_rebuild)
	Shell.favorites_changed.connect(_rebuild)
	Shell.bridge.status_updated.connect(_on_status)
	Shell.bridge.connection_changed.connect(func(_c): _on_status(Shell.bridge.status))
	_rebuild()
	_on_status({})


func _rebuild() -> void:
	var recent := Shell.recent_games(12)
	_hero_game = recent[0] if not recent.is_empty() else (Shell.games[0] if not Shell.games.is_empty() else {})
	if _hero_game.is_empty():
		_hero_title.text = "Игры не найдены"
		_hero_sub.text = "Steam-библиотека пуста или недоступна"
		_hero_btn.visible = false
	else:
		_hero_btn.visible = true
		_hero_title.text = _hero_game.name
		_hero_sub.text = "Последний запуск: %s · %s" % [UI.fmt_last_played(_hero_game.last_played), UI.fmt_playtime(_hero_game.playtime_min)]
		_hero_tex.texture = null
		var art: Dictionary = _hero_game.art
		Shell.load_art(art.get("hero", art.get("header", "")), func(t): _hero_tex.texture = t)
	for c in _rows.get_children():
		c.queue_free()
	_add_row("Недавно играли", recent.slice(1) if recent.size() > 1 else recent)
	_add_row("Избранное", Shell.favorite_games())
	if recent.is_empty():
		_add_row("Библиотека", Shell.games.slice(0, 12))


func _add_row(name: String, list: Array) -> void:
	if list.is_empty():
		return
	_rows.add_child(UI.label(name, 20, UI.TEXT, true))
	var cards := []
	for g in list:
		var c := GameCard.make(g, Vector2(276, 129), "header")
		c.chosen.connect(app.open_game)
		cards.append(c)
	_rows.add_child(card_row(cards, 150))


func _on_status(_s: Dictionary) -> void:
	if not Shell.bridge.connected:
		_gfg.text = "GFG Extreme не подключён"
		_gfg.add_theme_color_override("font_color", UI.TEXT_DIM)
		return
	var s := Shell.bridge.status
	var fps = s.get("fps", {}).get("output")
	_gfg.add_theme_color_override("font_color", UI.TEXT)
	_gfg.text = "Режим: %s%s" % [UI.mode_name(str(s.get("mode", ""))), ("   ·   %d FPS" % int(fps)) if fps != null else ""]


func focus_default() -> void:
	if _hero_btn.visible:
		_hero_btn.grab_focus()
	else:
		super.focus_default()
