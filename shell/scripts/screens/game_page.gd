## Страница игры: hero, Играть / Установить, Избранное, info, GFG Autopilot (Battery/Balanced/Quality).
extends Screen

const MODES := [["budget", "Батарея"], ["balanced", "Баланс"], ["quality", "Качество"], ["autopilot", "Autopilot"]]

var game: Dictionary = {}
var _hero: TextureRect
var _logo: TextureRect
var _name: Label
var _play: Button
var _fav: Button
var _info: GridContainer
var _modes: HBoxContainer
var _gfg_note: Label


func _ready() -> void:
	title = "Игра"
	var top := Control.new()
	top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top.custom_minimum_size = Vector2(0, 330)
	top.clip_contents = true
	add_child(top)
	_hero = TextureRect.new()
	_hero.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_hero.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_hero.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	top.add_child(_hero)
	var grad := TextureRect.new()
	var gt := GradientTexture2D.new()
	gt.gradient = Gradient.new()
	gt.gradient.set_color(0, Color(UI.BG, 0.0))
	gt.gradient.set_color(1, UI.BG)
	gt.fill_from = Vector2(0, 0)
	gt.fill_to = Vector2(0, 1)
	grad.texture = gt
	grad.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	grad.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	top.add_child(grad)
	_logo = TextureRect.new()
	_logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT
	_logo.position = Vector2(40, 40)
	_logo.size = Vector2(420, 160)
	top.add_child(_logo)
	_name = UI.label("", 36, UI.TEXT, true)
	_name.position = Vector2(40, 150)
	top.add_child(_name)

	var body := UI.hbox(24)
	body.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	body.offset_top = 236
	body.offset_left = 40
	body.offset_right = -40
	body.offset_bottom = -16
	add_child(body)
	var left := UI.vbox(14)
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_child(left)
	var actions := UI.hbox(12)
	left.add_child(actions)
	_play = UI.button("▶  Играть", true, 220, 56)
	_play.pressed.connect(_on_play)
	actions.add_child(_play)
	_fav = UI.button("", false, 200, 56)
	_fav.pressed.connect(func(): Shell.toggle_favorite(game); _refresh())
	actions.add_child(_fav)
	var dl := UI.button("Загрузки Steam", false, 0, 56)
	dl.pressed.connect(func(): OS.create_process(GameRunner.steam_command(), ["steam://open/downloads"]))
	actions.add_child(dl)
	var info_p := UI.panel(UI.CARD, 18)
	_info = GridContainer.new()
	_info.columns = 2
	_info.add_theme_constant_override("h_separation", 28)
	_info.add_theme_constant_override("v_separation", 8)
	info_p.add_child(_info)
	left.add_child(info_p)

	var right := UI.panel(UI.CARD, 18)
	right.custom_minimum_size = Vector2(470, 0)
	right.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	body.add_child(right)
	var rv := UI.vbox(12)
	right.add_child(rv)
	rv.add_child(UI.label("GFG AUTOPILOT", 15, UI.RED, true))
	_modes = UI.hbox(8)
	rv.add_child(_modes)
	for m in MODES:
		var b := UI.button(m[1], false, 104, 48)
		b.set_meta("mode", m[0])
		b.pressed.connect(_set_mode.bind(m[0]))
		_modes.add_child(b)
	_gfg_note = UI.label("", 14, UI.TEXT_DIM)
	_gfg_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	rv.add_child(_gfg_note)
	Shell.bridge.status_updated.connect(func(_s): _refresh_modes())
	Shell.bridge.connection_changed.connect(func(_c): _refresh_modes())


func enter(args: Dictionary = {}) -> void:
	game = args.get("game", {})
	title = str(game.get("name", "Игра"))
	_hero.texture = null
	_logo.texture = null
	_name.visible = true
	var art: Dictionary = game.get("art", {})
	Shell.load_art(art.get("hero", art.get("header", "")), func(t): _hero.texture = t)
	if art.has("logo"):
		Shell.load_art(art.logo, func(t): _logo.texture = t; _name.visible = false)
	_refresh()


func _refresh() -> void:
	_name.text = str(game.get("name", ""))
	var installed: bool = game.get("installed", false)
	_play.text = "▶  Играть" if installed else "⭳  Установить"
	_fav.text = ("★  В избранном" if Shell.is_favorite(game) else "☆  В избранное")
	for c in _info.get_children():
		c.queue_free()
	var rows := [["Время в игре", UI.fmt_playtime(int(game.get("playtime_min", 0)))],
		["Последний запуск", UI.fmt_last_played(int(game.get("last_played", 0)))],
		["Тип", "Steam" if game.get("kind") == "steam" else "Не Steam"],
		["Размер", UI.fmt_size(int(game.get("size_bytes", 0)))],
		["ID", str(game.get("appid", ""))]]
	for r in rows:
		_info.add_child(UI.label(r[0], 16, UI.TEXT_DIM))
		_info.add_child(UI.label(r[1], 16, UI.TEXT))
	_refresh_modes()


func _refresh_modes() -> void:
	var on := Shell.bridge.connected
	var mode := str(Shell.bridge.status.get("mode", ""))
	for b in _modes.get_children():
		b.disabled = not on
		var active: bool = on and b.get_meta("mode") == mode
		b.add_theme_stylebox_override("normal", UI.box(UI.RED if active else UI.CARD_HI))
	if not on:
		_gfg_note.text = "GFG Extreme не подключён: режимы недоступны. Игра запускается как обычно."
	else:
		var p := str(Shell.bridge.status.get("profile", ""))
		_gfg_note.text = "Профиль GFG: %s. Режим применяет Governor GFG Extreme." % (p if p != "" else "—")


func _set_mode(mode: String) -> void:
	Shell.bridge.set_mode(mode, func(ok, r):
		if not ok:
			Log.warn("gfg", "set_mode failed: %s" % r.get("error", "?"))
			app.toast("Не удалось сменить режим: %s" % r.get("error", "?")))


func _on_play() -> void:
	if game.get("installed", false):
		app.start_game(game)
	else:
		Log.info("library", "install request %s" % game.get("appid"))
		OS.create_process(GameRunner.steam_command(), ["steam://install/%s" % game.get("appid")])
		app.toast("Установка открыта в Steam")


func focus_default() -> void:
	_play.grab_focus()
