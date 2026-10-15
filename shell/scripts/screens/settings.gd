## Настройки (mockup 05): icon sidebar (Система, Экран, Звук, Интернет, Контроллер,
## Хранилище, GFG Extreme, Диагностика, О GFG Shell) and grouped rows on the right.
## Values the shell cannot own (Wi-Fi choice, refresh rate) open Steam's own page.
extends Screen

const SECTIONS := [["system", "Система", "settings"], ["display", "Экран", "monitor"], ["audio", "Звук", "volume"],
	["internet", "Интернет", "wifi"], ["controller", "Контроллер", "gamepad"], ["storage", "Хранилище", "storage"],
	["gfg", "GFG Extreme", "bolt"], ["diag", "Диагностика", "info"], ["about", "О GFG Shell", "brush"]]

var _side: VBoxContainer
var _title: Label
var _pane: VBoxContainer
var _section := "display"


func _ready() -> void:
	title = "Настройки"
	var h := UI.hbox(0)
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	h.offset_left = 36
	h.offset_right = -36
	h.offset_top = 6
	h.offset_bottom = -14
	add_child(h)
	var sp := UI.panel(Color(0, 0, 0, 0), 8, 0)
	sp.custom_minimum_size = Vector2(330, 0)
	h.add_child(sp)
	_side = UI.vbox(4)
	sp.add_child(_side)
	for s in SECTIONS:
		var b := UI.row(s[2], s[1], "", null, 56)
		b.set_meta("section", s[0])
		b.focus_entered.connect(_show.bind(s[0]))
		b.pressed.connect(func():
			_show(s[0])
			var f := Screen._first_focusable(_pane)
			if f:
				f.grab_focus())
		_side.add_child(b)
	var sep := ColorRect.new()
	sep.color = UI.LINE
	sep.custom_minimum_size = Vector2(1, 0)
	h.add_child(UI.margin(sep, 14, 0, 18, 0))
	var right := UI.vbox(16)
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(right)
	_title = UI.label("", 38, UI.TEXT, "bold")
	right.add_child(_title)
	var sc := ScrollContainer.new()
	sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
	sc.follow_focus = true
	right.add_child(sc)
	_pane = UI.vbox(16)
	_pane.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var pm := UI.margin(_pane, 4, 4, 6, 20)
	pm.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(pm)
	_show(_section)


func enter(args: Dictionary = {}) -> void:
	if args.has("section"):
		_show(args.section)


func _show(sec: String) -> void:
	_section = sec
	for b in _side.get_children():
		var on: bool = b.get_meta("section") == sec
		b.add_theme_stylebox_override("normal", UI.box(UI.RED if on else Color(0, 0, 0, 0), Color.TRANSPARENT, 10))
	for c in _pane.get_children():
		_pane.remove_child(c)
		c.queue_free()
	for s in SECTIONS:
		if s[0] == sec:
			_title.text = s[1]
	call("_sec_" + sec)


func _card() -> VBoxContainer:
	var p := UI.panel(UI.CARD, 6, 14)
	var v := UI.vbox(2)
	p.add_child(v)
	_pane.add_child(p)
	return v


func _info(card: VBoxContainer, icon: String, title: String, sub: String, value: String, cb: Callable = Callable()) -> Button:
	var r := UI.row(icon, title, sub, UI.value_box(value) if cb.is_valid() else UI.label(value, 16, UI.TEXT_DIM, "medium"), 64)
	if cb.is_valid():
		r.pressed.connect(cb)
	card.add_child(r)
	return r


func _steam(uri: String) -> Callable:
	return func(): OS.create_process(GameRunner.steam_command(), [uri])


func _note(t: String) -> void:
	var l := UI.label(t, 14, UI.TEXT_DIM, "regular")
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_pane.add_child(UI.margin(l, 6, 0, 6, 0))


func _sec_system() -> void:
	var s := SystemInfo.summary()
	var c := _card()
	_info(c, "gamepad", "Устройство", "", str(s.get("device", "—")))
	_info(c, "settings", "SteamOS", str(s.get("build", "")), str(s.get("os_version", s.get("os", "—"))))
	_info(c, "info", "Ядро", "", str(s.get("kernel", "—")))
	var c2 := _card()
	_info(c2, "bolt", "Процессор", "", str(s.get("cpu", "—")).replace("AMD Custom APU", "APU"))
	_info(c2, "monitor", "Графика", "", str(s.get("gpu", "—")))
	_info(c2, "storage", "Память", "", str(s.get("memory", "—")))


func _sec_display() -> void:
	var c := _card()
	var bright := GSliderRow.make("sun", "Яркость", SystemInfo.brightness_pct())
	bright.value_committed.connect(func(v):
		if not SystemInfo.set_brightness_pct(v):
			app.toast("Яркостью сейчас управляет Steam: «…» → Яркость"))
	c.add_child(bright)
	var hz := DisplayServer.screen_get_refresh_rate()
	_info(c, "monitor", "Частота обновления", "Более плавное изображение", ("%d Гц" % int(round(hz))) if hz > 0 else "—",
		_steam("steam://open/settings/display"))
	var s := DisplayServer.screen_get_size()
	_info(c, "display", "Разрешение", "Экран Steam Deck", "%d×%d" % [s.x, s.y])
	_note("Частоту, ночной режим и масштаб интерфейса задаёт Steam — строки открывают его настройки.")


func _sec_audio() -> void:
	var c := _card()
	var vol := GSliderRow.make("volume", "Громкость", SystemInfo.volume_pct())
	vol.value_committed.connect(func(v): SystemInfo.set_volume_pct(v))
	c.add_child(vol)
	_info(c, "volume", "Устройства вывода", "Наушники, Bluetooth, HDMI", "Steam", _steam("steam://open/settings/audio"))


func _sec_internet() -> void:
	var n := SystemInfo.network()
	var ssid := SystemInfo.wifi_name()
	var c := _card()
	_info(c, "wifi", "Wi-Fi", "Выбор сети и пароль — в настройках Steam",
		ssid if ssid != "" else ("подключено" if n.get("online", false) else "нет сети"), _steam("steam://open/settings/internet"))
	_info(c, "globe", "Подключение", str(n.get("iface", "")), "в сети" if n.get("online", false) else "нет")


func _sec_controller() -> void:
	var c := _card()
	var pads := Input.get_connected_joypads()
	if pads.is_empty():
		_info(c, "gamepad", "Контроллер", "Не найден", "—")
	for id in pads:
		_info(c, "gamepad", Input.get_joy_name(id), "Через Steam Input", "#%d" % id)
	_info(c, "settings", "Раскладка Steam Input", "Кнопки, гироскоп, тачпады", "Steam", _steam("steam://open/settings/controller"))
	_note("GFG Shell не перехватывает контроллер: он получает геймпад от Steam Input, как любая игра.")


func _sec_storage() -> void:
	var c := _card()
	var seen := {}
	for lib in SteamLibrary.library_paths(Shell.library.steam_root) if Shell.library.steam_root != "" else []:
		var st := SystemInfo.storage(lib)
		if st.is_empty():
			continue
		var key := "%d" % st.total
		if seen.has(key):
			continue
		seen[key] = true
		var used: float = 1.0 - float(st.free) / max(1.0, float(st.total))
		var name := "Карта microSD" if lib.contains("/run/media") else "Внутренний SSD"
		_info(c, "storage", name, "%s · занято %d%%" % [UI.fmt_size(st.total), int(used * 100)], "свободно " + UI.fmt_size(st.free))
	if seen.is_empty():
		_info(c, "storage", "Хранилище", "Steam не найден", "—")
	var lc := _card()
	for r in Shell.library.scan:
		var title: String = "Библиотека Steam" if r.path == Shell.library.steam_root else r.path.get_file()
		var sub: String = r.path + ("" if r.exists else " · не найдена")
		var val: String = "%d игр" % r.games
		if r.tools or r.bad:
			val += " (+%d служ., %d ошиб.)" % [r.tools, r.bad]
		_info(lc, "library", title, sub, val)
	_info(lc, "refresh", "Обновить библиотеку", "Перечитать файлы Steam", "Обновить", func():
		Shell.reload_library()
		_show("storage")
		app.toast("Библиотека: %d игр" % Shell.games.size()))
	_info(_card(), "download", "Загрузки", "Обновления и очередь", "Открыть", func(): app.push("downloads"))


func _sec_gfg() -> void:
	var c := _card()
	_info(c, "bolt", "GFG Extreme", "Связь с плагином (GFG Bridge)",
		"подключено" if Shell.bridge.connected else "нет (%s)" % Shell.bridge.last_error)
	_info(c, "gauge", "Центр GFG", "FPS, температура, TDP, режимы", "Открыть", func(): app.push("gfg"))
	_note("TDP и частоты GPU выставляет только Governor GFG Extreme. GFG Shell передаёт выбор режима и не управляет питанием сам.")


func _sec_diag() -> void:
	var c := _card()
	_info(c, "download", "Собрать диагностику", "Архив на рабочий стол: журналы, библиотека, сессия", "Собрать", func():
		var p := Diagnostics.write_package()
		app.toast(("Сохранено: " + p) if p != "" else "Не удалось сохранить архив"))
	var crash: Button
	crash = _info(c, "close", "Проверка восстановления", "Аварийно завершить оболочку (Steam должен остаться)", "Нажать дважды", func():
		if crash.get_meta("armed", false):
			Log.warn("diag", "user-triggered crash test")
			OS.crash("GFG Shell recovery test (user-triggered)")
		crash.set_meta("armed", true)
		app.toast("Нажмите ещё раз, чтобы аварийно завершить GFG Shell"))
	_note("Журнал: " + Log.path)


func _sec_about() -> void:
	var c := _card()
	_info(c, "info", "Версия", "GFG Shell", str(ProjectSettings.get_setting("application/config/version")))
	_info(c, "settings", "Движок", "Godot", Engine.get_version_info().string)
	_info(c, "play", "Игровой клиент", "Запуск через steam://rungameid", "Steam")
	_info(_card(), "close", "Выйти из GFG Shell", "Вернуться в Steam", "Выйти", app.quit_shell)
	_note("GFG Shell — часть GFG Extreme, GPL-3.0-or-later. Шрифт Inter (OFL), движок Godot (MIT).")


func focus_default() -> void:
	for b in _side.get_children():
		if b.get_meta("section") == _section:
			b.grab_focus()
			return
