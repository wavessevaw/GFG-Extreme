## Steam Adapter — launch side. A game is always started *by Steam* (steam://rungameid/<id>),
## so DRM, Steam Input, the overlay, Proton, launch options, cloud sync and achievements are
## Steam's own path. The shell only watches for the game's process tree and never kills it
## or Steam.
##
## Detection: Steam wraps a launched title in `reaper SteamLaunch AppId=<id> -- ...` and
## sets SteamGameId in the game's environment. Either marker (any of the game's ids)
## tells "running" and "exited"; returning focus is a fallback for titles without one.
class_name GameRunner
extends Node

signal state_changed(state: String, game: Dictionary)
signal launch_failed(game: Dictionary, reason: String)

const LAUNCH_TIMEOUT_S := 180.0   # Steam may update, sync cloud saves or show a dialog first
const SCAN_PERIOD_ACTIVE_S := 1.0
const SCAN_PERIOD_IDLE_S := 4.0

var state := "idle"               # idle | launching | running | exited
var game: Dictionary = {}
var running_appid := 0            # AppId seen in the process tree (also games started outside the shell)
var _launch_started := 0.0
var _scan_accum := 0.0
var _proc_root := "/proc"
var _last_launch_cmd: PackedStringArray = PackedStringArray()
var _env_floor := 0               # only processes newer than the launch have their environment read
## launch id string (AppId or 64-bit game id) -> library game ({} if unknown); set by the shell state.
var resolve_game: Callable = func(_id): return {}


func _ready() -> void:
	var r := OS.get_environment("GFG_SHELL_PROC_ROOT")
	if r != "":
		_proc_root = r


static func steam_command() -> String:
	var env := OS.get_environment("GFG_SHELL_STEAM_CMD")
	if env != "":
		return env
	for c in ["/usr/bin/steam", "/usr/games/steam"]:
		if FileAccess.file_exists(c):
			return c
	return "steam"


static func launch_uri(g: Dictionary) -> String:
	return "steam://rungameid/" + str(g.get("launch_id", g.get("appid", "")))


func launch(g: Dictionary) -> bool:
	if state == "launching" or state == "running":
		Log.warn("runner", "launch ignored: %s already %s" % [game.get("name", "?"), state])
		return false
	var uri := launch_uri(g)
	var cmd := steam_command()
	_last_launch_cmd = PackedStringArray([cmd, uri])
	Log.info("runner", "launch %s via %s %s" % [g.get("name", "?"), cmd, uri])
	var pid := OS.create_process(cmd, [uri])
	if pid <= 0:
		_set_state("idle", g)
		launch_failed.emit(g, "steam-command-failed")
		return false
	game = g
	_launch_started = Time.get_ticks_msec() / 1000.0
	_env_floor = max(1, max_pid(_proc_root) - 64)
	_set_state("launching", g)
	return true


func cancel_wait() -> void:
	# Stops *waiting*; the game (if Steam still starts it) is not touched.
	if state == "launching":
		Log.info("runner", "launch wait cancelled by user")
		_set_state("idle", game)


func _process(delta: float) -> void:
	_scan_accum += delta
	var period := SCAN_PERIOD_ACTIVE_S if state in ["launching", "running"] else SCAN_PERIOD_IDLE_S
	if _scan_accum < period:
		return
	_scan_accum = 0.0
	poll()


func poll() -> void:
	var procs := scan_processes(_proc_root, _env_floor if state in ["launching", "running"] else 0)
	match state:
		"launching":
			if _matches(procs, game):
				running_appid = int(game.get("appid", 0))
				Log.info("runner", "game %s detected" % game.get("name", "?"))
				_set_state("running", game)
			elif Time.get_ticks_msec() / 1000.0 - _launch_started > LAUNCH_TIMEOUT_S:
				Log.warn("runner", "no process for %s after %ds; SteamLaunch seen: %s" % [game.get("name", "?"),
					int(LAUNCH_TIMEOUT_S), str(procs.filter(func(p): return p.launch != "").map(func(p): return p.launch))])
				launch_failed.emit(game, "timeout")
				_set_state("idle", game)
		"running":
			if not _matches(procs, game):
				Log.info("runner", "game %s exited" % game.get("name", "?"))
				running_appid = 0
				_set_state("exited", game)
				_set_state("idle", game)
		_:
			# A game started outside the shell (Steam UI, another launcher) is still tracked.
			var other := ""
			for p in procs:
				if p.launch != "":
					other = p.launch
					break
			if other != "":
				var g: Dictionary = resolve_game.call(other)
				if g.is_empty():
					g = {"appid": int(other) if other.length() <= 10 else 0, "name": "Игра " + other, "id": other,
						"launch_id": other}
				if int(g.get("appid", 0)) != running_appid or running_appid == 0:
					game = g
					running_appid = int(g.get("appid", 0))
					_set_state("running", game)
			else:
				running_appid = 0


## The ids a running game can be known by: its AppId (Steam games), the unsigned and
## signed 32-bit shortcut id, and the 64-bit game id used in steam://rungameid.
static func game_ids(g: Dictionary) -> Array:
	var ids := []
	var appid := int(g.get("appid", 0))
	if appid > 0:
		ids.append(str(appid))
		if appid >= 0x80000000:
			ids.append(str(appid - 0x100000000))
	var lid := str(g.get("launch_id", ""))
	if lid != "" and not ids.has(lid):
		ids.append(lid)
	return ids


static func _matches(procs: Array, g: Dictionary) -> bool:
	var ids := game_ids(g)
	if ids.is_empty():
		return false
	for p in procs:
		if (p.launch != "" and ids.has(p.launch)) or (p.env_game != "" and ids.has(p.env_game)):
			return true
	return false


func _set_state(s: String, g: Dictionary) -> void:
	if s == state and s != "exited":
		return
	state = s
	state_changed.emit(s, g)


## Every process that carries a Steam launch marker: `reaper SteamLaunch AppId=<id>` in
## its command line, or (for processes newer than env_floor) SteamGameId=<id> in its
## environment — Steam sets that for the whole game tree, non-Steam shortcuts included.
static func scan_processes(proc_root: String = "/proc", env_floor: int = 0) -> Array:
	var out := []
	var dir := DirAccess.open(proc_root)
	if dir == null:
		return out
	for pid in dir.get_directories():
		if not pid.is_valid_int():
			continue
		var launch := ""
		var f := FileAccess.open(proc_root + "/" + pid + "/cmdline", FileAccess.READ)
		if f != null:
			# /proc reports length 0; read a bounded chunk instead of get_as_text().
			var raw := f.get_buffer(8192)
			if not raw.is_empty():
				launch = parse_steamlaunch_value(raw)
		var env_game := ""
		if env_floor > 0 and int(pid) >= env_floor:
			var e := FileAccess.open(proc_root + "/" + pid + "/environ", FileAccess.READ)
			if e != null:
				env_game = env_value(e.get_buffer(65536), "SteamGameId")
				if env_game == "0":
					env_game = ""
		if launch != "" or env_game != "":
			out.append({"pid": int(pid), "launch": launch, "env_game": env_game})
	return out


## AppIds (unsigned 32-bit) of every live `SteamLaunch AppId=<n>` process (tests, diagnostics).
static func scan_running_appids(proc_root: String = "/proc") -> Array:
	var out := []
	for p in scan_processes(proc_root, 0):
		var v: String = p.launch
		if v.is_valid_int() and v.length() <= 11:
			var id := int(v) & 0xFFFFFFFF
			if not out.has(id):
				out.append(id)
	return out


## Returns the AppId value from a NUL-separated cmdline containing "SteamLaunch" "AppId=<n>", else 0.
static func parse_steamlaunch_cmdline(raw: PackedByteArray) -> int:
	var v := parse_steamlaunch_value(raw)
	if v.is_valid_int() and v.length() <= 11:
		return int(v) & 0xFFFFFFFF
	return 0


## The raw AppId string after the SteamLaunch marker (may be a 64-bit game id), else "".
static func parse_steamlaunch_value(raw: PackedByteArray) -> String:
	var parts := _split_nul(raw)
	var has_marker := false
	for i in parts.size():
		var p: String = parts[i]
		if p == "--":
			break
		if p == "SteamLaunch":
			has_marker = true
		elif has_marker and p.begins_with("AppId="):
			var v := p.substr(6)
			return v if v.is_valid_int() else ""
	return ""


static func env_value(raw: PackedByteArray, key: String) -> String:
	var prefix := key + "="
	for entry in _split_nul(raw):
		if entry.begins_with(prefix):
			return entry.substr(prefix.length())
	return ""


static func max_pid(proc_root: String = "/proc") -> int:
	var best := 0
	var dir := DirAccess.open(proc_root)
	if dir != null:
		for pid in dir.get_directories():
			if pid.is_valid_int():
				best = max(best, int(pid))
	return best


static func _split_nul(raw: PackedByteArray) -> PackedStringArray:
	var out := PackedStringArray()
	var start := 0
	for i in raw.size():
		if raw[i] == 0:
			if i > start:
				out.append(raw.slice(start, i).get_string_from_utf8())
			start = i + 1
	if start < raw.size():
		out.append(raw.slice(start).get_string_from_utf8())
	return out
