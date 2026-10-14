## GFG Shell root: top bar with tabs, page stack, Quick panel, power menu, launch screen, toasts.
## Controller map: D-pad/stick move, A select, B back, L1/R1 tabs, View = Quick panel,
## Menu = power menu, X = search. Steam keeps the Steam and "..." buttons.
extends Control

const TABS := [["home", "Главная"], ["library", "Библиотека"], ["search", "Поиск"], ["gfg", "GFG"], ["settings", "Настройки"]]
const PAGE_SCRIPTS := {
	"home": "res://scripts/screens/home.gd", "library": "res://scripts/screens/library.gd",
	"search": "res://scripts/screens/search.gd", "gfg": "res://scripts/screens/gfg_center.gd",
	"settings": "res://scripts/screens/settings.gd", "game": "res://scripts/screens/game_page.gd",
}

var tab := "home"
var stack: Array = []            # pushed page names on top of the tab
var pages := {}
var _content: Control
var _tab_buttons := {}
var _clock: Label
var _battery: Label
var _bridge_dot: Label
var _hints: Label
var _quick: QuickPanel
var _power: PowerMenu
var _launch: LaunchScreen
var _toast: Label
var _toast_left := 0.0
var _status_accum := 0.0


func _ready() -> void:
	theme = UI.theme()
	var bg := ColorRect.new()
	bg.color = UI.BG
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	_build_top_bar()
	_content = Control.new()
	_content.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_content.offset_top = 72
	_content.offset_bottom = -40
	add_child(_content)
	_build_hint_bar()
	_quick = QuickPanel.new()
	_quick.app = self
	add_child(_quick)
	_power = PowerMenu.new()
	_power.app = self
	add_child(_power)
	_launch = LaunchScreen.new()
	_launch.app = self
	add_child(_launch)
	_toast = UI.label("", 17)
	_toast.add_theme_stylebox_override("normal", UI.box(Color(0.1, 0.1, 0.12, 0.95), UI.RED_DIM, 10, 14))
	_toast.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_toast.position.y -= 90
	_toast.visible = false
	add_child(_toast)
	Shell.game_state_changed.connect(_on_game_state)
	Shell.runner.launch_failed.connect(func(g, reason): _launch.failed(g, reason))
	_update_status()
	go_tab("home")
	_handle_cmdline()


func _build_top_bar() -> void:
	var bar := Panel.new()
	bar.add_theme_stylebox_override("panel", UI.box(UI.BG2, Color.TRANSPARENT, 0, 0))
	bar.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	bar.custom_minimum_size = Vector2(0, 64)
	add_child(bar)
	var h := UI.hbox(8)
	h.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	h.offset_left = 28
	h.offset_right = -28
	bar.add_child(h)
	var logo := UI.label("GFG", 28, UI.RED, true)
	logo.custom_minimum_size = Vector2(90, 0)
	logo.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(logo)
	h.add_child(UI.label("L1", 13, UI.TEXT_DIM))
	for t in TABS:
		var b := Button.new()
		b.text = t[1]
		b.flat = true
		b.focus_mode = Control.FOCUS_NONE   # tabs switch with L1/R1, focus stays in the page
		b.custom_minimum_size = Vector2(120, 64)
		b.add_theme_font_size_override("font_size", 19)
		b.pressed.connect(go_tab.bind(t[0]))
		_tab_buttons[t[0]] = b
		h.add_child(b)
	h.add_child(UI.label("R1", 13, UI.TEXT_DIM))
	h.add_child(UI.spacer())
	_bridge_dot = UI.label("● GFG", 15, UI.TEXT_DIM)
	_bridge_dot.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(_bridge_dot)
	_battery = UI.label("", 17, UI.TEXT)
	_battery.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(_battery)
	_clock = UI.label("", 19, UI.TEXT, true)
	_clock.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(_clock)


func _build_hint_bar() -> void:
	var bar := Panel.new()
	bar.add_theme_stylebox_override("panel", UI.box(UI.BG2, Color.TRANSPARENT, 0, 0))
	bar.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bar.offset_top = -40
	add_child(bar)
	_hints = UI.label("Ⓐ Выбрать    Ⓑ Назад    L1/R1 Разделы    ⧉ Быстрое меню    ☰ Питание    Ⓧ Поиск", 15, UI.TEXT_DIM)
	_hints.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_hints.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_hints.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_hints.offset_right = -28
	bar.add_child(_hints)


func _page(name: String) -> Screen:
	if not pages.has(name):
		var s: Screen = load(PAGE_SCRIPTS[name]).new()
		s.app = self
		s.name = name
		s.visible = false
		_content.add_child(s)
		pages[name] = s
	return pages[name]


func _show_only(name: String, args: Dictionary = {}) -> void:
	for n in pages.keys():
		pages[n].visible = n == name
	var p := _page(name)
	p.visible = true
	p.enter(args)
	p.focus_default.call_deferred()


func go_tab(name: String, args: Dictionary = {}) -> void:
	tab = name
	stack.clear()
	for t in _tab_buttons.keys():
		var b: Button = _tab_buttons[t]
		b.add_theme_color_override("font_color", UI.TEXT if t == name else UI.TEXT_DIM)
		b.add_theme_color_override("font_hover_color", UI.TEXT)
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color.TRANSPARENT
		sb.border_width_bottom = 3 if t == name else 0
		sb.border_color = UI.RED
		b.add_theme_stylebox_override("normal", sb)
		b.add_theme_stylebox_override("hover", sb)
	_show_only(name, args)
	Log.info("nav", "tab " + name)


func push(name: String, args: Dictionary = {}) -> void:
	stack.append({"name": name, "focus": get_viewport().gui_get_focus_owner()})
	_show_only(name, args)


func pop() -> void:
	if stack.is_empty():
		if tab != "home":
			go_tab("home")
		return
	var top: Dictionary = stack.pop_back()
	var under: String = stack.back().name if not stack.is_empty() else tab
	for n in pages.keys():
		pages[n].visible = n == under
	var f: Variant = top.get("focus")
	if f != null and is_instance_valid(f) and f.is_visible_in_tree():
		f.grab_focus()
	else:
		pages[under].focus_default()


func open_game(g: Dictionary) -> void:
	if g.is_empty():
		return
	push("game", {"game": g})


func start_game(g: Dictionary) -> void:
	_launch.begin(g)
	if not Shell.launch(g):
		_launch.failed(g, "steam-command-failed")


func show_power_menu() -> void:
	_power.open()


func toast(text: String, secs: float = 3.0) -> void:
	_toast.text = text
	_toast.visible = true
	_toast.reset_size()
	_toast.position.x = (size.x - _toast.size.x) / 2.0
	_toast_left = secs
	Log.info("toast", text)


func quit_shell() -> void:
	Log.info("app", "user quit")
	get_tree().quit()


func _on_game_state(state: String, g: Dictionary) -> void:
	Log.info("app", "game state %s: %s" % [state, g.get("name", "?")])
	match state:
		"running":
			_launch.running(g)
		"exited":
			_launch.close()
			if not (stack.size() > 0 and stack.back().name == "game"):
				open_game(Shell.library_game_by_appid(int(g.get("appid", 0))))
			toast("С возвращением в GFG Shell")
		"idle":
			if _launch.visible and _launch.phase != "failed":
				_launch.close()


func _input(event: InputEvent) -> void:
	if _launch.visible:
		if event.is_action_pressed("ui_cancel"):
			_launch.on_back()
			get_viewport().set_input_as_handled()
		return
	if _power.visible or _quick.visible:
		if event.is_action_pressed("ui_cancel") or (_quick.visible and event.is_action_pressed("shell_quick")):
			(_power if _power.visible else _quick).close()
			get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("shell_quick"):
		_quick.open()
	elif event.is_action_pressed("shell_menu"):
		_power.open()
	elif event.is_action_pressed("shell_tab_next") or event.is_action_pressed("shell_tab_prev"):
		var i := TABS.map(func(t): return t[0]).find(tab)
		i = wrapi(i + (1 if event.is_action_pressed("shell_tab_next") else -1), 0, TABS.size())
		go_tab(TABS[i][0])
	elif event.is_action_pressed("shell_search") and not (get_viewport().gui_get_focus_owner() != null and pages.has("search") and pages.search.visible):
		go_tab("search")
	elif event.is_action_pressed("shell_option"):
		var top: String = stack.back().name if not stack.is_empty() else tab
		if top == "game":
			Shell.toggle_favorite(pages.game.game)
			pages.game._refresh()
		else:
			return
	elif event.is_action_pressed("ui_cancel"):
		var top2: String = stack.back().name if not stack.is_empty() else tab
		if not pages[top2].back():
			pop()
	else:
		return
	get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	if _toast_left > 0:
		_toast_left -= delta
		if _toast_left <= 0:
			_toast.visible = false
	_status_accum += delta
	if _status_accum >= 5.0:
		_status_accum = 0.0
		_update_status()
	if get_viewport().gui_get_focus_owner() == null and not _launch.visible:
		var top: String = stack.back().name if not stack.is_empty() else tab
		if pages.has(top) and pages[top].visible:
			pages[top].focus_default()


func _update_status() -> void:
	_clock.text = Time.get_time_string_from_system().substr(0, 5)
	var b := SystemInfo.battery()
	_battery.text = ("%s %d%%" % ["⚡" if b.charging else "▮", b.percent]) if b.available else ""
	_bridge_dot.add_theme_color_override("font_color", UI.GREEN if Shell.bridge.connected else UI.TEXT_DIM)


func _notification(what: int) -> void:
	# Out of focus (a game or Steam on top): idle at a few frames per second.
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		Engine.max_fps = 10
	elif what == NOTIFICATION_APPLICATION_FOCUS_IN and Shell.runner.state != "running":
		Engine.max_fps = 0


## Test/CI hooks: --gfg-page=<tab> and --gfg-screenshot=<png> (after the library settles).
func _handle_cmdline() -> void:
	var page := ""
	var shot := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--gfg-page="):
			page = a.substr(11)
		elif a.begins_with("--gfg-screenshot="):
			shot = a.substr(17)
	if page != "":
		if page.begins_with("game:"):
			var g := Shell.library_game_by_appid(int(page.substr(5)))
			open_game(g)
		elif page == "quick":
			_quick.open()
		elif page == "power":
			_power.open()
		elif page == "launch":
			_launch.begin(Shell.games[0] if not Shell.games.is_empty() else {})
		elif PAGE_SCRIPTS.has(page):
			go_tab(page)
	if shot != "":
		await get_tree().create_timer(3.0).timeout
		var img := get_viewport().get_texture().get_image()
		img.save_png(shot)
		Log.info("app", "screenshot " + shot)
		get_tree().quit()
