## Global shell state (autoload "Shell"): library, GFG favorites, settings, the game runner
## and the GFG Bridge. Screens read from here and listen to its signals.
extends Node

signal library_changed
signal favorites_changed
signal game_state_changed(state: String, game: Dictionary)

const STATE_FILE := "user://state.json"

var library := SteamLibrary.new()
var games: Array = []
var runner: GameRunner
var bridge: BridgeClient
var favorites := {}     # game id -> bool; GFG's own list, overrides Steam's Favorites collection
var settings := {"sort": "name", "filter": "all"}
var art_cache := {}     # path -> Texture2D
var _art_loading := {}
var _art_pending: Array = []      # shared with the loader thread (guarded by _art_mutex)
var _art_mutex := Mutex.new()
var _art_sem := Semaphore.new()
var _art_thread: Thread
var _art_quit := false


func _ready() -> void:
	_setup_input()
	_load_state()
	runner = GameRunner.new()
	runner.name = "GameRunner"
	runner.resolve_game = library_game_by_launch
	add_child(runner)
	runner.state_changed.connect(_on_runner_state)
	runner.launch_failed.connect(func(g, reason): Log.warn("runner", "launch failed: %s (%s)" % [g.get("name", "?"), reason]))
	bridge = BridgeClient.new()
	bridge.name = "Bridge"
	add_child(bridge)
	_art_thread = Thread.new()
	_art_thread.start(_art_worker)
	reload_library()


## Controller actions on top of Godot's ui_* defaults (which already cover D-pad, left
## stick, A = accept, B = cancel). Steam Input presents the Deck as an XInput pad, so
## these are standard SDL button indices.
func _setup_input() -> void:
	var map := {
		"shell_tab_prev": [JOY_BUTTON_LEFT_SHOULDER, KEY_Q],
		"shell_tab_next": [JOY_BUTTON_RIGHT_SHOULDER, KEY_E],
		"shell_quick": [JOY_BUTTON_BACK, KEY_TAB],
		"shell_menu": [JOY_BUTTON_START, KEY_M],
		"shell_option": [JOY_BUTTON_Y, KEY_F],
		"shell_search": [JOY_BUTTON_X, KEY_SLASH],
	}
	# Godot 4 leaves A/B unbound for ui_accept/ui_cancel (only Enter/Escape): bind them.
	var a := InputEventJoypadButton.new()
	a.button_index = JOY_BUTTON_A
	InputMap.action_add_event("ui_accept", a)
	var b := InputEventJoypadButton.new()
	b.button_index = JOY_BUTTON_B
	InputMap.action_add_event("ui_cancel", b)
	for action in map.keys():
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		var pad := InputEventJoypadButton.new()
		pad.button_index = map[action][0]
		InputMap.action_add_event(action, pad)
		var ev := InputEventKey.new()
		ev.keycode = map[action][1]
		InputMap.action_add_event(action, ev)


func reload_library() -> void:
	var t0 := Time.get_ticks_msec()
	games = library.load_library()
	Log.info("library", "%d games (root=%s, account=%s) in %d ms, errors=%s" % [games.size(),
		library.steam_root, library.account_id, Time.get_ticks_msec() - t0, ",".join(library.errors)])
	library_changed.emit()


func library_game_by_appid(appid: int) -> Dictionary:
	for g in games:
		if int(g.appid) == appid:
			return g
	return {}


func library_game_by_launch(id: String) -> Dictionary:
	for g in games:
		if GameRunner.game_ids(g).has(id):
			return g
	return {}


func is_favorite(g: Dictionary) -> bool:
	var id := str(g.get("id", ""))
	if favorites.has(id):
		return favorites[id]
	return g.get("steam_favorite", false)


func toggle_favorite(g: Dictionary) -> void:
	favorites[str(g.id)] = not is_favorite(g)
	_save_state()
	favorites_changed.emit()


func recent_games(limit: int = 12) -> Array:
	var r := games.filter(func(g): return int(g.last_played) > 0)
	r.sort_custom(func(a, b): return int(a.last_played) > int(b.last_played))
	return r.slice(0, limit)


func favorite_games() -> Array:
	return games.filter(func(g): return is_favorite(g))


func filtered_games(filter: String, sort: String) -> Array:
	var r: Array
	match filter:
		"installed": r = games.filter(func(g): return g.installed)
		"favorites": r = favorite_games()
		"recent": r = recent_games(1000)
		"nonsteam": r = games.filter(func(g): return g.kind == "shortcut")
		_: r = games.duplicate()
	if sort == "recent" and filter != "recent":
		r.sort_custom(func(a, b): return int(a.last_played) > int(b.last_played))
	return r


func search(query: String) -> Array:
	var q := query.strip_edges().to_lower()
	if q == "":
		return []
	var starts := []
	var contains := []
	for g in games:
		var n := str(g.name).to_lower()
		if n.begins_with(q):
			starts.append(g)
		elif n.contains(q):
			contains.append(g)
	return starts + contains


func launch(g: Dictionary) -> bool:
	return runner.launch(g)


func _on_runner_state(state: String, g: Dictionary) -> void:
	# While a game runs the shell drops to a few frames per second: it must not steal GPU/CPU.
	if state == "running":
		Engine.max_fps = 10
		bridge.active = false
	elif state == "idle":
		Engine.max_fps = 0
		bridge.active = true
	if state == "exited":
		reload_library()   # LastPlayed / playtime changed
	game_state_changed.emit(state, g)


## Loads artwork off the main thread; cb(texture) is called on the main thread.
func load_art(path: String, cb: Callable) -> void:
	if path == "":
		return
	if art_cache.has(path):
		cb.call(art_cache[path])
		return
	if _art_loading.has(path):
		_art_loading[path].append(cb)
		return
	_art_loading[path] = [cb]
	_art_mutex.lock()
	_art_pending.append(path)
	_art_mutex.unlock()
	_art_sem.post()


## One loader thread with a queue: decoding stays off the main thread, and the thread is
## joined on exit (pool tasks still running at quit corrupted the heap in testing).
func _art_worker() -> void:
	while true:
		_art_sem.wait()
		_art_mutex.lock()
		var quit := _art_quit
		var path: String = _art_pending.pop_front() if not _art_pending.is_empty() else ""
		_art_mutex.unlock()
		if quit:
			return
		if path == "":
			continue
		var img := Image.load_from_file(path)
		_art_loaded.call_deferred(path, img)


func _exit_tree() -> void:
	_art_mutex.lock()
	_art_quit = true
	_art_mutex.unlock()
	_art_sem.post()
	if _art_thread != null and _art_thread.is_started():
		_art_thread.wait_to_finish()


func _art_loaded(path: String, img: Image) -> void:
	var tex: Texture2D = null
	if img != null and not img.is_empty():
		tex = ImageTexture.create_from_image(img)
		art_cache[path] = tex
	for cb in _art_loading.get(path, []):
		if cb.is_valid() and tex != null:
			cb.call(tex)
	_art_loading.erase(path)


func _load_state() -> void:
	if not FileAccess.file_exists(STATE_FILE):
		return
	var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(STATE_FILE))
	if d is Dictionary:
		if d.get("favorites") is Dictionary:
			favorites = d.favorites
		if d.get("settings") is Dictionary:
			settings.merge(d.settings, true)


func _save_state() -> void:
	var f := FileAccess.open(STATE_FILE, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify({"favorites": favorites, "settings": settings}))


func set_setting(key: String, value: Variant) -> void:
	settings[key] = value
	_save_state()
