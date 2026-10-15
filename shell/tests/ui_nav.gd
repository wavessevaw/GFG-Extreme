## Controller navigation end to end on the real main scene (headless):
## A presses, B goes back/closes, overlays keep focus inside, L1/R1 switch tabs.
## godot --headless --path shell -s res://tests/ui_nav.gd  (GFG_SHELL_STEAM_ROOT=fixture)
extends SceneTree

var app: Control
var fails := 0
var checks := 0
var step := 0
var wait := 0


func check(c: bool, what: String) -> void:
	checks += 1
	if not c:
		fails += 1
		printerr("FAIL: " + what)


func pad(button: int) -> void:
	for pressed in [true, false]:
		var e := InputEventJoypadButton.new()
		e.button_index = button
		e.pressed = pressed
		Input.parse_input_event(e)
	Input.flush_buffered_events()


func focus() -> Control:
	return app.get_viewport().gui_get_focus_owner()


func _initialize() -> void:
	app = load("res://main.tscn").instantiate()
	root.add_child(app)


func _process(_d: float) -> bool:
	wait += 1
	if wait < 20:
		return false
	wait = 0
	match step:
		0:
			check(app.current_page() == "home", "starts on home")
			check(focus() != null and focus().get_parent() != null, "home has focus")
			pad(JOY_BUTTON_START)                     # main menu
		1:
			check(app._menu.visible, "Menu opens the side menu")
			var before := focus()
			check(app._menu.is_ancestor_of(before), "focus moved into the menu")
			for i in 12:
				pad(JOY_BUTTON_DPAD_DOWN)
			check(app._menu.is_ancestor_of(focus()), "D-pad stays inside the menu")
			for i in 3:
				pad(JOY_BUTTON_DPAD_RIGHT)
			check(app._menu.is_ancestor_of(focus()), "right does not leak to the tiles behind")
			pad(JOY_BUTTON_B)
		2:
			check(not app._menu.visible, "B closes the menu")
			app.show_power_menu()
		3:
			check(app._power.visible and app._power.is_ancestor_of(focus()), "power menu owns focus")
			for i in 6:
				pad(JOY_BUTTON_DPAD_DOWN)
			check(app._power.is_ancestor_of(focus()), "power menu keeps focus on D-pad")
			pad(JOY_BUTTON_DPAD_UP)                    # from «Выйти» up to «Выключение»
			pad(JOY_BUTTON_A)                         # -> confirmation (no power action)
		4:
			check(app._power.visible and app._power._confirm != "", "A pressed a power row (confirmation shown)")
			pad(JOY_BUTTON_B)
		5:
			check(not app._power.visible, "B closes the power menu")
			pad(JOY_BUTTON_RIGHT_SHOULDER)
		6:
			check(app.current_page() == "library", "R1 -> library")
			pad(JOY_BUTTON_A)                          # open the focused game
		7:
			check(app.current_page() == "game", "A on a tile opens the game page")
			pad(JOY_BUTTON_B)
		8:
			check(app.current_page() == "library", "B returns to the library")
			pad(JOY_BUTTON_BACK)
		9:
			check(app._quick.visible and app._quick.is_ancestor_of(focus()), "View opens Quick settings with focus")
			pad(JOY_BUTTON_BACK)
		10:
			check(not app._quick.visible, "View closes Quick settings")
			print("ui nav: %d checks, %d failures" % [checks, fails])
			quit(fails)
			return true
	step += 1
	return false
