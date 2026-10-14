## Настройки: Steam-style sidebar (Экран, Звук, Сеть, Загрузки, Питание, Система, GFG Extreme,
## Диагностика, О GFG Shell) and a detail pane.
extends Screen

const SECTIONS := [["display", "Экран"], ["audio", "Звук"], ["network", "Сеть"], ["downloads", "Загрузки"],
	["power", "Питание"], ["system", "Система"], ["gfg", "GFG Extreme"], ["diag", "Диагностика"], ["about", "О GFG Shell"]]

var _side: VBoxContainer
var _pane: VBoxContainer
var _section := "display"


func _ready() -> void:
	title = "Настройки"
	var h := UI.hbox(24)
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(UI.margin(h, 32, 12, 32, 12))
	get_child(0).set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var sp := UI.panel(UI.BG2, 10)
	sp.custom_minimum_size = Vector2(280, 0)
	h.add_child(sp)
	_side = UI.vbox(6)
	sp.add_child(_side)
	for s in SECTIONS:
		var b := UI.button(s[1], false, 0, 50)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.set_meta("section", s[0])
		b.focus_entered.connect(_show.bind(s[0]))
		b.pressed.connect(func(): _show(s[0]); var f := Screen._first_focusable(_pane); if f: f.grab_focus())
		_side.add_child(b)
	var pp := UI.panel(UI.CARD, 22)
	pp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(pp)
	_pane = UI.vbox(14)
	pp.add_child(_pane)
	_show(_section)


func enter(args: Dictionary = {}) -> void:
	if args.has("section"):
		_show(args.section)


func _show(sec: String) -> void:
	_section = sec
	for b in _side.get_children():
		b.add_theme_stylebox_override("normal", UI.box(UI.RED_DIM if b.get_meta("section") == sec else UI.CARD))
	for c in _pane.get_children():
		c.queue_free()
	var name: String = ""
	for s in SECTIONS:
		if s[0] == sec:
			name = s[1]
	_pane.add_child(UI.label(name, 26, UI.TEXT, true))
	call("_sec_" + sec)


func _row(k: String, v: String) -> void:
	var h := UI.hbox(12)
	var kl := UI.label(k, 17, UI.TEXT_DIM)
	kl.custom_minimum_size = Vector2(260, 0)
	h.add_child(kl)
	var vl := UI.label(v, 17, UI.TEXT)
	vl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(vl)
	_pane.add_child(h)


func _note(t: String) -> void:
	var l := UI.label(t, 14, UI.TEXT_DIM)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_pane.add_child(l)


func _sec_display() -> void:
	var b := SystemInfo.brightness_pct()
	_row("Яркость", ("%d%%" % b) if b >= 0 else "—")
	_row("Разрешение", "%dx%d" % [DisplayServer.screen_get_size().x, DisplayServer.screen_get_size().y])
	var hz := DisplayServer.screen_get_refresh_rate()
	_row("Частота", ("%d Гц" % int(round(hz))) if hz > 0 else "—")
	_note("Яркостью и частотой экрана управляет Steam/gamescope (кнопки быстрого меню Steam). GFG Shell их только показывает.")


func _sec_audio() -> void:
	var lbl := UI.label("", 17)
	var upd := func(): var v := SystemInfo.volume_pct(); lbl.text = "Громкость: " + (("%d%%" % v) if v >= 0 else "—")
	upd.call()
	_pane.add_child(lbl)
	var h := UI.hbox(10)
	for step in [-10, 10]:
		var bt := UI.button("Громкость %s" % ("−" if step < 0 else "+"), false, 200, 50)
		bt.pressed.connect(func(): SystemInfo.change_volume(step); upd.call())
		h.add_child(bt)
	_pane.add_child(h)


func _sec_network() -> void:
	var n := SystemInfo.network()
	_row("Подключение", ("в сети (%s)" % n.iface) if n.online else "нет подключения")
	_row("Тип", ("Wi-Fi" if n.get("wifi", false) else "проводное/другое") if n.online else "—")
	_note("Выбор сети Wi-Fi — в настройках Steam (кнопка ниже откроет их).")
	var b := UI.button("Открыть настройки Steam", false, 300, 50)
	b.pressed.connect(func(): OS.create_process(GameRunner.steam_command(), ["steam://open/settings"]))
	_pane.add_child(b)


func _sec_downloads() -> void:
	_note("Загрузки, обновления и установка игр выполняет Steam.")
	var b := UI.button("Открыть загрузки Steam", true, 300, 50)
	b.pressed.connect(func(): OS.create_process(GameRunner.steam_command(), ["steam://open/downloads"]))
	_pane.add_child(b)
	var r := UI.button("Обновить библиотеку", false, 300, 50)
	r.pressed.connect(func(): Shell.reload_library(); app.toast("Библиотека: %d игр" % Shell.games.size()))
	_pane.add_child(r)


func _sec_power() -> void:
	var bat := SystemInfo.battery()
	_row("Батарея", ("%d%% %s" % [bat.percent, "(заряжается)" if bat.charging else ""]) if bat.available else "—")
	var b := UI.button("Меню питания", true, 300, 50)
	b.pressed.connect(app.show_power_menu)
	_pane.add_child(b)


func _sec_system() -> void:
	var s := SystemInfo.summary()
	for k in [["Устройство", "device"], ["ОС", "os"], ["Сборка", "build"], ["Ядро", "kernel"], ["CPU", "cpu"], ["GPU", "gpu"], ["Память", "memory"]]:
		_row(k[0], str(s.get(k[1], "—")))
	_row("Steam", Shell.library.steam_root if Shell.library.steam_root != "" else "не найден")
	_row("Игр в библиотеке", str(Shell.games.size()))


func _sec_gfg() -> void:
	_row("Подключение", "есть" if Shell.bridge.connected else "нет (%s)" % Shell.bridge.last_error)
	var b := UI.button("Открыть центр GFG", true, 300, 50)
	b.pressed.connect(func(): app.go_tab("gfg"))
	_pane.add_child(b)
	_note("TDP и частоты GPU выставляет только Governor GFG Extreme. GFG Shell передаёт выбор режима и не управляет питанием сам.")


func _sec_diag() -> void:
	_note("Соберёт архив на рабочий стол: журналы оболочки, сводку библиотеки, окружение сессии, атомы gamescope, процессы Steam. Пришлите его разработчику.")
	var b := UI.button("Собрать диагностику", true, 300, 50)
	b.pressed.connect(func():
		var p := Diagnostics.write_package()
		app.toast(("Сохранено: " + p) if p != "" else "Не удалось сохранить архив"))
	_pane.add_child(b)
	_row("Журнал", Log.path)
	_note("Проверка восстановления (тест H6): оболочка аварийно завершится, Steam должен остаться рабочим. Запущенные игры не затрагиваются.")
	var crash := UI.button("Аварийно завершить оболочку", false, 300, 50)
	crash.pressed.connect(func():
		if crash.get_meta("armed", false):
			Log.warn("diag", "user-triggered crash test")
			OS.crash("GFG Shell recovery test (user-triggered)")
		crash.set_meta("armed", true)
		crash.text = "Нажмите ещё раз для подтверждения")
	_pane.add_child(crash)


func _sec_about() -> void:
	_row("Версия", str(ProjectSettings.get_setting("application/config/version")))
	_row("Движок", "Godot " + Engine.get_version_info().string)
	_row("Игровой клиент", "Steam (запуск через steam://rungameid)")
	_note("GFG Shell — оболочка GFG Extreme. Лицензия GPL-3.0-or-later. Выход из оболочки возвращает в штатный режим Steam.")
	var b := UI.button("Выйти из GFG Shell", false, 300, 50)
	b.pressed.connect(app.quit_shell)
	_pane.add_child(b)


func focus_default() -> void:
	for b in _side.get_children():
		if b.get_meta("section") == _section:
			b.grab_focus()
			return
