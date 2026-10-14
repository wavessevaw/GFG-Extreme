## Steam Adapter — launch side. A game is always started *by Steam* (steam://rungameid/<id>),
## so DRM, Steam Input, the overlay, Proton, launch options, cloud sync and achievements are
## Steam's own path. The shell only watches for the game's process tree and never kills it
## or Steam.
##
## Detection: Steam wraps every launched title in `reaper SteamLaunch AppId=<id> -- ...`.
## A /proc scan for that marker tells "running" and "exited" for Steam and non-Steam titles.
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
## appid -> library game Dictionary ({} if unknown); set by the shell state.
var resolve_game: Callable = func(_appid): return {}


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
	var ids := scan_running_appids(_proc_root)
	var target := int(game.get("appid", 0))
	match state:
		"launching":
			if target != 0 and ids.has(target):
				running_appid = target
				_set_state("running", game)
			elif Time.get_ticks_msec() / 1000.0 - _launch_started > LAUNCH_TIMEOUT_S:
				Log.warn("runner", "no SteamLaunch process for %d after %ds" % [target, int(LAUNCH_TIMEOUT_S)])
				launch_failed.emit(game, "timeout")
				_set_state("idle", game)
		"running":
			if not ids.has(target):
				Log.info("runner", "game %d exited" % target)
				running_appid = 0
				_set_state("exited", game)
				_set_state("idle", game)
		_:
			# A game started outside the shell (Steam UI, another launcher) is still tracked.
			if not ids.is_empty():
				var other: int = ids[0]
				if other != running_appid:
					running_appid = other
					game = resolve_game.call(other)
					if game.is_empty():
						game = {"appid": other, "name": "AppId %d" % other, "id": str(other)}
					_set_state("running", game)
			else:
				running_appid = 0


func _set_state(s: String, g: Dictionary) -> void:
	if s == state and s != "exited":
		return
	state = s
	state_changed.emit(s, g)


## AppIds of every live `SteamLaunch AppId=<n>` process under proc_root.
static func scan_running_appids(proc_root: String = "/proc") -> Array:
	var out := []
	var dir := DirAccess.open(proc_root)
	if dir == null:
		return out
	for pid in dir.get_directories():
		if not pid.is_valid_int():
			continue
		var f := FileAccess.open(proc_root + "/" + pid + "/cmdline", FileAccess.READ)
		if f == null:
			continue
		# /proc reports length 0; read a bounded chunk instead of get_as_text().
		var raw := f.get_buffer(8192)
		if raw.is_empty():
			continue
		var appid := parse_steamlaunch_cmdline(raw)
		if appid > 0 and not out.has(appid):
			out.append(appid)
	return out


## Returns the AppId from a NUL-separated cmdline containing "SteamLaunch" "AppId=<n>", else 0.
static func parse_steamlaunch_cmdline(raw: PackedByteArray) -> int:
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
			if v.is_valid_int():
				return int(v) & 0xFFFFFFFF
	return 0


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
