## Страница игры (mockup 03): full-bleed art, logo, Играть + ⚙, info chips, the GFG
## Autopilot card (switch + Battery / Balanced / Quality) and a library card.
extends Screen

const MODES := [["budget", "Battery", "battery"], ["balanced", "Balanced", "gauge"], ["quality", "Quality", "star"], ["autopilot", "Auto", ""]]
const WOLF := preload("res://assets/gfg_wolf.png")

var game: Dictionary = {}
var _logo: TextureRect
var _logo_box: Control
const TITLE_BOX := 120.0
const LOGO_MAX := Vector2(560, 130)
var _name: Label
var _play: Button
var _gear: Button
var _chips: HBoxContainer
var _auto_row: Button
var _auto_sw: GSwitch
var _auto_desc: Label
var _seg: HBoxContainer
var _fav_row: Button
var _fav_sw: GSwitch
var _type_row: Button
var _last_manual := "balanced"


func _ready() -> void:
	title = "Игра"
	var v := UI.vbox(0)
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 52
	v.offset_right = -52
	v.offset_top = 22
	v.offset_bottom = -24
	add_child(v)
	var logo_box := Control.new()
	_logo_box = logo_box
	logo_box.custom_minimum_size = Vector2(0, TITLE_BOX)
	v.add_child(logo_box)
	_logo = TextureRect.new()
	_logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT
	_logo.position = Vector2(0, 6)
	_logo.size = LOGO_MAX
	logo_box.add_child(_logo)
	_name = UI.label("", 58, UI.TEXT, "bold")
	_name.position = Vector2(0, 18)
	_name.size = Vector2(1100, 90)
	_name.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	logo_box.add_child(_name)
	var actions := UI.hbox(14)
	_play = UI.button("Играть", true, 230, 64, "play")
	_play.pressed.connect(_on_play)
	actions.add_child(_play)
	_gear = UI.icon_button("gear", 64)
	_gear.pressed.connect(func():
		OS.create_process(GameRunner.steam_command(), ["steam://nav/games/details/%s" % game.get("appid", "")]))
	actions.add_child(_gear)
	v.add_child(actions)
	v.add_child(_gap(18))
	_chips = UI.hbox(12)
	v.add_child(_chips)
	v.add_child(UI.spacer(false))
	var cards := UI.hbox(18)
	v.add_child(cards)
	# GFG Autopilot card
	var ap := UI.panel(Color(0.07, 0.07, 0.09, 0.94), 20, 16)
	ap.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ap.size_flags_stretch_ratio = 1.55
	var av := UI.vbox(10)
	ap.add_child(av)
	_auto_sw = GSwitch.make(false)
	_auto_row = Button.new()
	_auto_row.focus_mode = Control.FOCUS_ALL
	_auto_row.custom_minimum_size = Vector2(0, 50)
	_auto_row.add_theme_stylebox_override("normal", UI.box(Color(0, 0, 0, 0), Color.TRANSPARENT, 10))
	_auto_row.add_theme_stylebox_override("hover", UI.box(Color(1, 1, 1, 0.04), Color.TRANSPARENT, 10))
	_auto_row.add_theme_stylebox_override("focus", UI.focus_box(UI.RED, 10))
	_auto_row.add_theme_stylebox_override("disabled", UI.box(Color(0, 0, 0, 0), Color.TRANSPARENT, 10))
	var ah := UI.hbox(10)
	ah.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var am := UI.margin(ah, 8, 0, 8, 0)
	am.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	am.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_auto_row.add_child(am)
	var wolf := TextureRect.new()
	wolf.texture = WOLF
	wolf.custom_minimum_size = Vector2(34, 34)
	wolf.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	wolf.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	wolf.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ah.add_child(wolf)
	ah.add_child(UI.label("GFG", 24, UI.TEXT, "bold"))
	ah.add_child(UI.label("Autopilot", 24, UI.TEXT, "medium"))
	ah.add_child(UI.spacer())
	ah.add_child(_auto_sw)
	_auto_row.pressed.connect(_toggle_autopilot)
	av.add_child(_auto_row)
	_auto_desc = UI.label("", 14, UI.TEXT_DIM, "regular")
	av.add_child(UI.margin(_auto_desc, 8, 0, 8, 0))
	# modes as tiles: icon on top, name under it; Auto carries the wolf
	_seg = UI.hbox(10)
	for m in MODES:
		var b := Button.new()
		b.focus_mode = Control.FOCUS_ALL
		b.custom_minimum_size = Vector2(0, 78)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_stylebox_override("focus", UI.focus_box(UI.TEXT, 14))
		b.set_meta("mode", m[0])
		b.set_meta("icon", m[2])
		b.pressed.connect(_set_mode.bind(m[0]))
		var col := UI.vbox(6)
		col.alignment = BoxContainer.ALIGNMENT_CENTER
		col.mouse_filter = Control.MOUSE_FILTER_IGNORE
		col.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		var ic: Control
		if m[2] == "":
			var w := TextureRect.new()
			w.texture = WOLF
			w.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			w.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			ic = w
		else:
			ic = GIcon.make(m[2], 24, UI.TEXT_DIM)
		ic.name = "Icon"
		ic.custom_minimum_size = Vector2(26, 26)
		ic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		col.add_child(ic)
		var l := UI.label(m[1], 16, UI.TEXT_DIM, "semibold")
		l.name = "Name"
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		col.add_child(l)
		b.add_child(col)
		_seg.add_child(b)
	av.add_child(_seg)
	cards.add_child(ap)
	# library card
	var lc := UI.panel(Color(0.07, 0.07, 0.09, 0.94), 12, 16)
	lc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var lv := UI.vbox(2)
	lc.add_child(lv)
	lv.add_child(UI.margin(UI.label("Библиотека", 20, UI.TEXT, "bold"), 10, 6, 0, 4))
	_fav_sw = GSwitch.make(false)
	_fav_row = UI.row("star", "Избранное", "", _fav_sw, 56)
	_fav_row.pressed.connect(func(): Shell.toggle_favorite(game); _refresh())
	lv.add_child(_fav_row)
	_type_row = UI.row("info", "Свойства в Steam", "", GIcon.make("chevron", 16, UI.TEXT_DIM), 56)
	_type_row.pressed.connect(func():
		OS.create_process(GameRunner.steam_command(), ["steam://nav/games/details/%s" % game.get("appid", "")]))
	lv.add_child(_type_row)
	cards.add_child(lc)
	Shell.bridge.status_updated.connect(func(_s): if visible: _refresh_modes())
	Shell.bridge.connection_changed.connect(func(_c): if visible: _refresh_modes())


func _gap(h: int) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(1, h)
	return c


func hints() -> Array:
	return [["A", "Выбрать"], ["B", "Назад"], ["Y", "Избранное"], ["X", "Поиск"]]


func option() -> bool:
	Shell.toggle_favorite(game)
	_refresh()
	return true


func enter(args: Dictionary = {}) -> void:
	if args.has("game"):
		game = args.game
	title = str(game.get("name", "Игра"))
	_logo.texture = null
	_logo_box.custom_minimum_size.y = TITLE_BOX
	_name.visible = true
	var art: Dictionary = game.get("art", {})
	app.set_backdrop(art.get("hero", art.get("header", "")))
	if art.has("logo"):
		Shell.load_art(art.logo, func(t):
			_logo.texture = t
			_name.visible = false
			# the box follows the logo's drawn height: the buttons sit right under it
			_logo_box.custom_minimum_size.y = 18.0 + minf(LOGO_MAX.y,
				LOGO_MAX.x * float(t.get_height()) / maxf(1.0, float(t.get_width()))))
	_refresh()


func _refresh() -> void:
	_name.text = str(game.get("name", ""))
	var installed: bool = game.get("installed", false)
	(_play.get_child(0).get_child(1) as Label).text = "Играть" if installed else "Установить"
	for c in _chips.get_children():
		c.queue_free()
	var pt := UI.fmt_playtime(int(game.get("playtime_min", 0)))
	_chips.add_child(UI.chip("clock", pt if pt != "—" else "Ещё не играли"))
	_chips.add_child(UI.chip("refresh", "Последний запуск", UI.fmt_last_played(int(game.get("last_played", 0)))))
	if int(game.get("size_bytes", 0)) > 0:
		_chips.add_child(UI.chip("storage", UI.fmt_size(int(game.size_bytes)), "на диске"))
	if game.get("update_pending", false):
		_chips.add_child(UI.chip("download", "Есть обновление"))
	if game.get("kind") == "shortcut":
		_chips.add_child(UI.chip("gamepad", "Не Steam"))
	_fav_sw.on = Shell.is_favorite(game)
	_refresh_modes()


func _refresh_modes() -> void:
	var on := Shell.bridge.connected
	var mode := str(Shell.bridge.status.get("mode", ""))
	if mode in ["budget", "balanced", "quality"]:
		_last_manual = mode
	_auto_sw.unknown = not on
	_auto_sw.on = mode == "autopilot"
	_auto_row.disabled = not on
	for b in _seg.get_children():
		b.disabled = not on
		var active: bool = on and b.get_meta("mode") == mode
		var sb := UI.box(Color(UI.RED, 0.20) if active else Color(1, 1, 1, 0.035),
			UI.RED if active else Color(1, 1, 1, 0.07), 14)
		sb.set_border_width_all(2 if active else 1)
		for st in ["normal", "pressed", "disabled"]:
			b.add_theme_stylebox_override(st, sb)
		b.add_theme_stylebox_override("hover", sb if active else UI.box(Color(1, 1, 1, 0.06), Color(1, 1, 1, 0.1), 14))
		b.modulate.a = 1.0 if on else 0.5
		var lab: Label = b.get_child(0).get_node("Name")
		lab.add_theme_color_override("font_color", UI.TEXT if active else UI.TEXT_DIM)
		var ic = b.get_child(0).get_node("Icon")
		if ic is GIcon:
			ic.set_icon(b.get_meta("icon"), UI.RED.lightened(0.25) if active else UI.TEXT_DIM)
	if not on:
		_auto_desc.text = "GFG Extreme не подключён. Игра запускается как обычно."
	elif mode == "autopilot":
		_auto_desc.text = "Автоматически подбирает оптимальные настройки для вашего устройства."
	else:
		_auto_desc.text = "Фиксированный режим %s. Включите Autopilot, чтобы GFG подбирал сам." % UI.mode_name(mode)


func _toggle_autopilot() -> void:
	var mode := str(Shell.bridge.status.get("mode", ""))
	_set_mode(_last_manual if mode == "autopilot" else "autopilot")


func _set_mode(mode: String) -> void:
	Shell.bridge.set_mode(mode, func(ok, r):
		if not ok:
			app.toast("Не удалось сменить режим: %s" % r.get("error", "?"))
		Shell.bridge.call_method("status", {}, func(ok2, st):
			if ok2:
				Shell.bridge.status = st
				Shell.bridge.status_updated.emit(st)))


func _on_play() -> void:
	if game.get("installed", false):
		app.start_game(game)
	else:
		Log.info("library", "install request %s" % game.get("appid"))
		OS.create_process(GameRunner.steam_command(), ["steam://install/%s" % game.get("appid")])
		app.toast("Установка открыта в Steam")


func focus_default() -> void:
	_play.grab_focus()
