## Главная (mockup 01): full-bleed art of the game in focus, its logo, Играть / ···,
## then «Недавно играли». The first tile is the game to continue; moving along the row
## swaps the art behind, as Steam's home does.
extends Screen

var _hero_game: Dictionary = {}
var _kicker: Label
var _kicker_box: HBoxContainer
var _logo: TextureRect
var _title: Label
var _logo_box: Control
const TITLE_BOX := 118.0
const LOGO_MAX := Vector2(520, 110)
var _sub: Label
var _play: Button
var _more: Button
var _row_box: VBoxContainer
var _empty: Label


func _ready() -> void:
	title = "Главная"
	var v := UI.vbox(0)
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 52
	v.offset_right = -52
	v.offset_top = 34
	v.offset_bottom = -26
	add_child(v)
	_kicker_box = UI.kicker("Продолжить игру")
	_kicker = _kicker_box.get_node("Text")
	v.add_child(_kicker_box)
	var logo_box := Control.new()
	_logo_box = logo_box
	logo_box.custom_minimum_size = Vector2(0, TITLE_BOX)
	v.add_child(logo_box)
	_logo = TextureRect.new()
	_logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT
	_logo.position = Vector2(0, 14)
	_logo.size = LOGO_MAX
	logo_box.add_child(_logo)
	_title = UI.label("", 64, UI.TEXT, "bold")
	_title.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.45))
	_title.add_theme_constant_override("shadow_offset_y", 3)
	_title.add_theme_constant_override("shadow_outline_size", 8)
	_title.position = Vector2(0, 22)
	_title.size = Vector2(1000, 90)
	_title.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	logo_box.add_child(_title)
	_sub = UI.label("", 16, UI.TEXT_DIM, "medium")
	v.add_child(_sub)
	v.add_child(_gap(16))
	var actions := UI.hbox(14)
	_play = UI.button("Играть", true, 230, 64, "play")
	_play.pressed.connect(func(): if not _hero_game.is_empty(): _activate(_hero_game))
	actions.add_child(_play)
	_more = UI.icon_button("dots", 64)
	_more.pressed.connect(func(): if not _hero_game.is_empty(): app.open_game(_hero_game))
	actions.add_child(_more)
	v.add_child(actions)
	v.add_child(UI.spacer(false))
	_row_box = UI.vbox(12)
	v.add_child(_row_box)
	_empty = UI.label("Игры не найдены: Steam-библиотека пуста или недоступна.", 18, UI.TEXT_DIM, "medium")
	_empty.visible = false
	v.add_child(_empty)
	Shell.library_changed.connect(_rebuild)
	Shell.favorites_changed.connect(_rebuild)
	_rebuild()


func _gap(h: int) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(1, h)
	return c


func enter(_args: Dictionary = {}) -> void:
	_show_hero(_hero_game)


func _rebuild() -> void:
	for c in _row_box.get_children():
		c.queue_free()
	var recent := Shell.recent_games(12)
	var list := recent if not recent.is_empty() else Shell.games.slice(0, 12)
	_empty.visible = list.is_empty()
	_play.visible = not list.is_empty()
	_more.visible = not list.is_empty()
	if list.is_empty():
		_hero_game = {}
		_kicker.text = ""
		_title.text = "GFG Shell"
		_sub.text = ""
		return
	_row_box.add_child(UI.label("Недавно играли" if not recent.is_empty() else "Библиотека", 21, UI.TEXT, "bold"))
	var cards := []
	for g in list:
		var c := GameCard.make(g, Vector2(156, 234), "grid")
		c.chosen.connect(app.open_game)
		c.focused.connect(_show_hero)
		cards.append(c)
	_row_box.add_child(card_row(cards, 236, 20))
	_show_hero(list[0])


func _show_hero(g: Dictionary) -> void:
	if g.is_empty():
		return
	_hero_game = g
	var recent := Shell.recent_games(1)
	_kicker.text = ("Продолжить игру" if (not recent.is_empty() and recent[0].id == g.id) else "Недавно играли").to_upper()
	_title.text = g.name
	_title.visible = true
	_logo.texture = null
	_logo_box.custom_minimum_size.y = TITLE_BOX
	var played := UI.fmt_last_played(int(g.last_played))
	var pt := UI.fmt_playtime(int(g.playtime_min))
	_sub.text = "Последний запуск: %s%s" % [played, ("  ·  " + pt) if pt != "—" else ""]
	_play.get_child(0).get_child(1).text = "Играть" if g.get("installed", false) else "Установить"
	var art: Dictionary = g.get("art", {})
	if visible:
		app.set_backdrop(art.get("hero", art.get("header", "")))
	if art.has("logo"):
		var gid: String = g.id
		Shell.load_art(art.logo, func(t):
			if _hero_game.get("id") == gid:
				_logo.texture = t
				_title.visible = false
				# the box follows the logo's drawn height: the buttons sit right under it
				var hs := minf(LOGO_MAX.y, LOGO_MAX.x * float(t.get_height()) / maxf(1.0, float(t.get_width())))
				_logo_box.custom_minimum_size.y = hs + 30.0)


func _activate(g: Dictionary) -> void:
	if g.get("installed", false):
		app.start_game(g)
	else:
		app.open_game(g)


func focus_default() -> void:
	if _play.visible:
		_play.grab_focus()
	else:
		super.focus_default()
