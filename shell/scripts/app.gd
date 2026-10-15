## GFG Shell root, laid out as the GFG/SteamOS concept sheets: transparent top bar with
## red pill tabs (Главная / Библиотека / Магазин) over full-bleed game art, content,
## hint bar with controller glyphs. Overlays (menu, quick settings, power) own the
## controller while open.
## Controller: D-pad/stick move · A select · B back · L1/R1 tabs · Menu = main menu ·
## View = Quick settings · X = search · Y = favourite. Steam and "…" stay Steam's.
extends Control

const TABS := [["home", "Главная"], ["library", "Библиотека"], ["store", "Магазин"]]
const PAGE_SCRIPTS := {
	"home": "res://scripts/screens/home.gd", "library": "res://scripts/screens/library.gd",
	"store": "res://scripts/screens/store.gd", "search": "res://scripts/screens/search.gd",
	"gfg": "res://scripts/screens/gfg_center.gd", "settings": "res://scripts/screens/settings.gd",
	"downloads": "res://scripts/screens/downloads.gd", "game": "res://scripts/screens/game_page.gd",
}
const TOP_H := 76
const BOTTOM_H := 58

var tab := "home"
var stack: Array = []            # pushed pages on top of the tab
var pages := {}
var backdrop: Control
var _content: Control
var _tab_buttons := {}
var _tab_pill: Panel
var _clock: Label
var _battery: Label
var _battery_icon: GIcon
var _wifi: GIcon
var _bridge_dot: Label
var _hints: HBoxContainer
var _menu: SideMenu
var _quick: QuickSettings
var _power: PowerMenu
var _launch: LaunchScreen
var _toast: Label
var _toast_left := 0.0
var _status_accum := 0.0
var _logged_inputs := 0


func _ready() -> void:
	theme = UI.theme()
	var bg := ColorRect.new()
	bg.color = UI.BG
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	backdrop = UI.hero_backdrop()
	backdrop.modulate.a = 0.0
	add_child(backdrop)
	var grain := ColorRect.new()
	grain.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	grain.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var gm := ShaderMaterial.new()
	gm.shader = preload("res://assets/shaders/grain.gdshader")
	grain.material = gm
	add_child(grain)
	_content = Control.new()
	_content.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_content.offset_top = TOP_H
	_content.offset_bottom = -BOTTOM_H
	add_child(_content)
	_build_top_bar()
	_build_hint_bar()
	_menu = SideMenu.new()
	_menu.app = self
	add_child(_menu)
	_quick = QuickSettings.new()
	_quick.app = self
	add_child(_quick)
	_power = PowerMenu.new()
	_power.app = self
	add_child(_power)
	_launch = LaunchScreen.new()
	_launch.app = self
	add_child(_launch)
	_toast = UI.label("", 17, UI.TEXT, "semibold")
	_toast.add_theme_stylebox_override("normal", UI.box(Color(0.08, 0.08, 0.1, 0.96), UI.RED_DIM, 12, 18))
	_toast.z_index = 80
	_toast.visible = false
	add_child(_toast)
	Shell.game_state_changed.connect(_on_game_state)
	Shell.runner.launch_failed.connect(func(g, reason): _launch.failed(g, reason))
	_update_status()
	_start_drift.call_deferred()
	go_tab("home")
	_handle_cmdline()


# ---------------------------------------------------------------- chrome
func _build_top_bar() -> void:
	var h := UI.hbox(10)
	h.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	h.offset_left = 36
	h.offset_right = -36
	h.offset_top = 14
	h.custom_minimum_size = Vector2(0, 48)
	add_child(h)
	var logo := TextureRect.new()   # the GFG wolf, as in the plugin
	logo.texture = preload("res://assets/gfg_wolf.png")
	logo.custom_minimum_size = Vector2(44, 44)
	logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	logo.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(logo)
	h.add_child(_gap(18))
	_tab_pill = Panel.new()
	var pill := UI.box(UI.RED, Color.TRANSPARENT, 22, 0)
	pill.shadow_color = Color(UI.RED, 0.35)
	pill.shadow_size = 10
	_tab_pill.add_theme_stylebox_override("panel", pill)
	_tab_pill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_tab_pill)
	move_child(_tab_pill, h.get_index())
	for t in TABS:
		var b := Button.new()
		b.text = t[1]
		b.focus_mode = Control.FOCUS_NONE   # L1/R1 switch tabs; focus stays in the page
		b.custom_minimum_size = Vector2(0, 44)
		b.add_theme_font_override("font", UI.font("semibold"))
		b.add_theme_font_size_override("font_size", 19)
		b.pressed.connect(go_tab.bind(t[0]))
		_tab_buttons[t[0]] = b
		h.add_child(b)
	h.add_child(UI.spacer())
	_bridge_dot = UI.label("●", 14, UI.MUTED, "bold")
	_bridge_dot.tooltip_text = "GFG Extreme"
	_bridge_dot.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(_bridge_dot)
	h.add_child(_gap(8))
	_wifi = GIcon.make("wifi", 24)
	h.add_child(_wifi)
	h.add_child(_gap(10))
	_battery = UI.label("", 18, UI.TEXT, "semibold")
	_battery.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(_battery)
	_battery_icon = GIcon.make("battery", 26)
	h.add_child(_battery_icon)
	h.add_child(_gap(14))
	_clock = UI.label("", 19, UI.TEXT, "semibold")
	_clock.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(_clock)


func _gap(w: int) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(w, 1)
	return c


func _build_hint_bar() -> void:
	var line := ColorRect.new()
	line.color = UI.LINE
	line.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	line.offset_top = -BOTTOM_H
	line.offset_bottom = -BOTTOM_H + 1
	add_child(line)
	var bar := UI.hbox(12)
	bar.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bar.offset_top = -BOTTOM_H
	bar.offset_left = 36
	bar.offset_right = -36
	add_child(bar)
	bar.add_child(UI.keycap("⧉"))
	bar.add_child(_vcenter(UI.label("Меню", 17, Color(UI.TEXT, 0.82), "semibold")))
	bar.add_child(_gap(10))
	bar.add_child(UI.keycap("☰"))
	bar.add_child(_vcenter(UI.label("Быстрые настройки", 17, Color(UI.TEXT, 0.82), "semibold")))
	bar.add_child(UI.spacer())
	_hints = UI.hbox(10)
	bar.add_child(_hints)
	set_hints([["A", "Выбрать"], ["B", "Назад"], ["X", "Поиск"]])


func _vcenter(c: Control) -> Control:
	c.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return c


func set_hints(list: Array) -> void:
	for c in _hints.get_children():
		c.queue_free()
	for i in list.size():
		if i > 0:
			_hints.add_child(_gap(14))
		_hints.add_child(UI.glyph(list[i][0]))
		_hints.add_child(_vcenter(UI.label(list[i][1], 17, UI.TEXT, "semibold")))


var _backdrop_gen := 0
var _backdrop_tween: Tween
var _backdrop_path := ""


## Shows game art behind the page: cross-fades from the art already there (or fades
## in over the plain background) and keeps the slow drift going. "" hides it;
## strength < 1 keeps it in the background (library, store).
func set_backdrop(path: String, strength: float = 1.0) -> void:
	# a generation counter: art that finishes loading after the page changed is dropped
	_backdrop_gen += 1
	var gen := _backdrop_gen
	if _backdrop_tween != null:
		_backdrop_tween.kill()
	if path == "":
		_backdrop_path = ""
		_backdrop_tween = create_tween()
		_backdrop_tween.tween_property(backdrop, "modulate:a", 0.0, FX.MED)
		return
	if path == _backdrop_path and backdrop.modulate.a > 0.0:
		_backdrop_tween = create_tween()
		_backdrop_tween.tween_property(backdrop, "modulate:a", strength, FX.MED)
		return
	Shell.load_art(path, func(t):
		if gen != _backdrop_gen:
			return
		_backdrop_path = path
		_set_accent(UI.accent_of(t))
		var cur: TextureRect = backdrop.get_node("Drift/Art")
		var nxt: TextureRect = backdrop.get_node("Drift/ArtNext")
		if _backdrop_tween != null:
			_backdrop_tween.kill()
		_backdrop_tween = create_tween().set_parallel(true)
		if backdrop.modulate.a < 0.05 or cur.texture == null:
			cur.texture = t
			nxt.modulate.a = 0.0
			_backdrop_tween.tween_property(backdrop, "modulate:a", strength, FX.SLOW)
		else:
			nxt.texture = t
			nxt.modulate.a = 0.0
			_backdrop_tween.tween_property(backdrop, "modulate:a", strength, FX.MED)
			_backdrop_tween.tween_property(nxt, "modulate:a", 1.0, 0.45).set_trans(Tween.TRANS_SINE)
			_backdrop_tween.chain().tween_callback(func():
				cur.texture = nxt.texture
				nxt.modulate.a = 0.0))


## The ambient light and the dust take the art's colour, cross-faded.
func _set_accent(c: Color) -> void:
	var glow: TextureRect = backdrop.get_node("Glow")
	var bloom: TextureRect = backdrop.get_node("Bloom")
	var gg: Gradient = (glow.texture as GradientTexture2D).gradient
	var bg: Gradient = (bloom.texture as GradientTexture2D).gradient
	var g0: Color = gg.get_color(0)
	var b0: Color = bg.get_color(0)
	var dust: CPUParticles2D = backdrop.get_node("Dust")
	var d0: Color = dust.color
	var t := create_tween()
	t.tween_method(func(k: float):
		gg.set_color(0, g0.lerp(Color(c, 0.30), k))
		bg.set_color(0, b0.lerp(Color(c.lerp(UI.RED, 0.5), 0.24), k))
		dust.color = d0.lerp(c.lerp(Color.WHITE, 0.6), k), 0.0, 1.0, 0.6).set_trans(Tween.TRANS_SINE)


## Parallax: the art shifts a little with the focus (x in -1..1 across a row).
func parallax(x: float) -> void:
	var drift: Control = backdrop.get_node("Drift")
	var base := Vector2(-UI.PARALLAX_PX, -UI.PARALLAX_PX)
	FX.to(drift, "position", base + Vector2(-clampf(x, -1.0, 1.0) * UI.PARALLAX_PX * 0.7, 0), 0.9,
		Tween.TRANS_SINE, Tween.EASE_OUT)


## Ken Burns: a slow, endless zoom of the art (6 % over 24 s, there and back).
func _start_drift() -> void:
	var drift: Control = backdrop.get_node("Drift")
	drift.pivot_offset = size * Vector2(0.62, 0.4)
	var t := create_tween().set_loops()
	t.tween_property(drift, "scale", Vector2(1.06, 1.06), 24.0).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	t.tween_property(drift, "scale", Vector2(1.0, 1.0), 24.0).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


# ---------------------------------------------------------------- navigation
func _page(name: String) -> Screen:
	if not pages.has(name):
		var s: Screen = load(PAGE_SCRIPTS[name]).new()
		s.app = self
		s.name = name
		s.visible = false
		_content.add_child(s)
		pages[name] = s
	return pages[name]


func current_page() -> String:
	return stack.back().name if not stack.is_empty() else tab


func _show_only(name: String, args: Dictionary = {}) -> void:
	for n in pages.keys():
		pages[n].visible = n == name
	var p := _page(name)
	p.visible = true
	set_backdrop("")
	p.enter(args)
	set_hints(p.hints())
	p.focus_default.call_deferred()
	FX.enter(p, Vector2(28, 0) if not stack.is_empty() else Vector2(0, 12), FX.MED)


func go_tab(name: String, args: Dictionary = {}) -> void:
	tab = name
	stack.clear()
	for t in _tab_buttons.keys():
		var b: Button = _tab_buttons[t]
		var active: bool = t == name
		var sb := UI.box(Color(0, 0, 0, 0), Color.TRANSPARENT, 22, 22)
		for st in ["normal", "hover", "pressed"]:
			b.add_theme_stylebox_override(st, sb)
		b.add_theme_color_override("font_color", UI.TEXT if active else UI.TEXT_DIM)
		b.add_theme_color_override("font_hover_color", UI.TEXT)
	_move_tab_pill.call_deferred(name)
	_show_only(name, args)
	Log.info("nav", "tab " + name)


## The red pill slides to the active tab (instant the first time).
func _move_tab_pill(name: String) -> void:
	var b: Button = _tab_buttons.get(name)
	if b == null or _tab_pill == null:
		return
	while b.size.x < 1.0 and is_inside_tree():   # first layout pass not done yet
		await get_tree().process_frame
	var r := Rect2(b.global_position - global_position, b.size)
	if _tab_pill.size.x < 1.0:
		_tab_pill.position = r.position
		_tab_pill.size = r.size
		return
	FX.to(_tab_pill, "position", r.position, FX.MED + 0.05, Tween.TRANS_QUART)
	FX.to(_tab_pill, "size", r.size, FX.MED + 0.05, Tween.TRANS_QUART)


func push(name: String, args: Dictionary = {}) -> void:
	stack.append({"name": name, "focus": get_viewport().gui_get_focus_owner()})
	_show_only(name, args)
	Log.info("nav", "push " + name)


func pop() -> void:
	if stack.is_empty():
		if tab != "home":
			go_tab("home")
		return
	var top: Dictionary = stack.pop_back()
	var under := current_page()
	for n in pages.keys():
		pages[n].visible = n == under
	set_backdrop("")
	pages[under].enter({"returning": true})
	set_hints(pages[under].hints())
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
	_toast.position = Vector2((size.x - _toast.size.x) / 2.0, size.y - BOTTOM_H - _toast.size.y - 18)
	_toast_left = secs
	Log.info("toast", text)


func quit_shell() -> void:
	Log.info("app", "user quit")
	get_tree().quit()


func _on_game_state(state: String, g: Dictionary) -> void:
	Log.info("app", "game state %s: %s" % [state, g.get("name", "?")])
	# Only launches started from the shell show the launch screen; a game started
	# from Steam's own UI is tracked silently.
	var ours: bool = _launch.visible
	if state == "running" or state == "launching":
		_back_during_game = false
	match state:
		"running":
			if ours:
				_launch.running(g)
		"exited":
			if ours:
				_launch.close()
				if current_page() != "game":
					open_game(Shell.library_game_by_appid(int(g.get("appid", 0))))
				toast("С возвращением в GFG Shell")
		"idle":
			if _launch.visible and _launch.phase != "failed":
				_launch.close()


func _active_overlay() -> Overlay:
	for o in [_power, _quick, _menu]:
		if o.visible:
			return o
	return null


func _input(event: InputEvent) -> void:
	if _logged_inputs < 40 and (event is InputEventJoypadButton or event is InputEventKey) and event.is_pressed():
		_logged_inputs += 1
		Log.info("input", "%s device=%d %s" % [event.get_class(), event.device, event.as_text()])
	if _input_blocked():
		# a game (or Steam) is on top: its buttons are not ours
		get_viewport().set_input_as_handled()
		return
	if _launch.visible:
		if event.is_action_pressed("ui_cancel"):
			_launch.on_back()
			get_viewport().set_input_as_handled()
		return
	var ov := _active_overlay()
	if ov != null:
		if event.is_action_pressed("ui_cancel") or (ov == _quick and event.is_action_pressed("shell_quick")) \
				or (ov == _menu and event.is_action_pressed("shell_menu")):
			ov.close()
			get_viewport().set_input_as_handled()
		elif ov.navigate(event):
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("shell_tab_next") or event.is_action_pressed("shell_tab_prev"):
			ov.on_tab(1 if event.is_action_pressed("shell_tab_next") else -1)
			get_viewport().set_input_as_handled()
		elif event.is_action_pressed("shell_search") or event.is_action_pressed("shell_option"):
			get_viewport().set_input_as_handled()   # nothing behind the overlay reacts
		return
	if event.is_action_pressed("shell_quick"):
		_quick.open()
	elif event.is_action_pressed("shell_menu"):
		_menu.open()
	elif event.is_action_pressed("shell_tab_next") or event.is_action_pressed("shell_tab_prev"):
		var i := TABS.map(func(t): return t[0]).find(tab)
		i = wrapi(i + (1 if event.is_action_pressed("shell_tab_next") else -1), 0, TABS.size())
		go_tab(TABS[i][0])
	elif event.is_action_pressed("shell_search") and current_page() != "search":
		push("search")
	elif event.is_action_pressed("shell_option"):
		if not pages[current_page()].option():
			return
	elif event.is_action_pressed("ui_cancel"):
		if not pages[current_page()].back():
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
		var ov := _active_overlay()
		if ov != null:
			ov._focus_first()
		elif pages.has(current_page()) and pages[current_page()].visible:
			pages[current_page()].focus_default()


func _update_status() -> void:
	_clock.text = Time.get_time_string_from_system().substr(0, 5)
	var b := SystemInfo.battery()
	_battery.text = ("%d%%" % b.percent) if b.available else ""
	_battery_icon.visible = b.available
	_battery_icon.set_icon("bolt" if b.get("charging", false) else "battery")
	_wifi.modulate.a = 1.0 if SystemInfo.network().get("online", false) else 0.35
	_bridge_dot.add_theme_color_override("font_color", UI.GREEN if Shell.bridge.connected else UI.MUTED)


var _focus_lost_at := -1.0
var _focused := true
var _ignore_until := 0.0          # the press that brought the shell back is not a command
var _back_during_game := false    # the player came back to the shell while the game still runs


## Joypad events reach the shell even while a game has the screen (Godot reads the pads
## directly). Nothing reacts to them while the shell is not focused, while a game runs
## (unless the player came back to the shell), or for a moment after the focus returns.
func _input_blocked() -> bool:
	if not _focused or Time.get_ticks_msec() / 1000.0 < _ignore_until:
		return true
	return Shell.runner.state == "running" and not _back_during_game


func _notification(what: int) -> void:
	# Out of focus (a game or Steam on top): idle at a few frames per second.
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		Engine.max_fps = 10
		_focused = false
		_focus_lost_at = Time.get_ticks_msec() / 1000.0
	elif what == NOTIFICATION_APPLICATION_FOCUS_IN:
		_focused = true
		_ignore_until = Time.get_ticks_msec() / 1000.0 + 0.4
		if Shell.runner.state == "running" and _focus_lost_at > 0:
			_back_during_game = true
		if Shell.runner.state != "running":
			Engine.max_fps = 0
		# Fallback for titles without a launch marker: the game took the screen and we
		# got it back, so it has ended — stop waiting instead of hanging on "Запуск…".
		var away := Time.get_ticks_msec() / 1000.0 - _focus_lost_at if _focus_lost_at > 0 else 0.0
		_focus_lost_at = -1.0
		if _launch.visible and _launch.phase == "launching" and away > 4.0:
			Log.warn("runner", "focus back after %.0f s without a detected game process; closing the launch screen" % away)
			Shell.runner.cancel_wait()
			_launch.close()
			toast("С возвращением в GFG Shell")


## Test/CI hooks: --gfg-page=<page|game:ID|quick[:gfg|sys]|menu|power|launch> and --gfg-screenshot=<png>.
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
			open_game(Shell.library_game_by_appid(int(page.substr(5))))
		elif page == "quick" or page.begins_with("quick:"):
			if page.begins_with("quick:"):
				_quick.tab = page.substr(6)
			_quick.open()
		elif page == "menu":
			_menu.open()
		elif page == "power":
			_power.open()
		elif page == "launch":
			_launch.begin(Shell.recent_games(1)[0] if not Shell.recent_games(1).is_empty() else {})
		elif page in ["home", "library", "store"]:
			go_tab(page)
		elif PAGE_SCRIPTS.has(page):
			push(page)
	if shot != "":
		await get_tree().create_timer(3.0).timeout
		if OS.get_cmdline_user_args().has("--gfg-motion"):
			# motion check: move the focus right, then a frame every 0.1 s (<shot>-<n>.png)
			var ev := InputEventAction.new()
			ev.action = "ui_right"
			ev.pressed = true
			Input.parse_input_event(ev)
			for n in 8:
				await get_tree().create_timer(0.1).timeout
				get_viewport().get_texture().get_image().save_png(shot.replace(".png", "-%d.png" % n))
		var img := get_viewport().get_texture().get_image()
		img.save_png(shot)
		Log.info("app", "screenshot " + shot)
		get_tree().quit()
