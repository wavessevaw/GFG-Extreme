## Diagnostics package: one zip on the Desktop with everything needed to judge a device run
## without remote access (shell logs, library scan summary, session environment, gamescope
## root atoms, Steam/gamescope processes, bridge state). No tokens or passwords are included.
class_name Diagnostics
extends RefCounted

const ENV_KEYS := ["XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "DISPLAY", "WAYLAND_DISPLAY",
	"GAMESCOPE_WAYLAND_DISPLAY", "SteamAppId", "SteamGameId", "STEAM_COMPAT_APP_ID", "SteamDeck", "SteamOS",
	"STEAM_RUNTIME", "SDL_GAMECONTROLLERCONFIG", "SDL_JOYSTICK_HIDAPI", "ENABLE_GAMESCOPE_WSI", "HOME", "USER"]


static func _run(cmd: String, args: Array) -> String:
	var out := []
	var code := OS.execute(cmd, args, out, true)
	return "$ %s %s\n(exit %d)\n%s" % [cmd, " ".join(args), code, "".join(out)]


static func collect() -> Dictionary:
	var env := {}
	for k in ENV_KEYS:
		env[k] = OS.get_environment(k)
	var lib := Shell.library
	var kinds := {"steam": 0, "shortcut": 0, "installed": 0, "with_grid": 0, "with_hero": 0}
	for g in Shell.games:
		kinds[g.kind] = kinds.get(g.kind, 0) + 1
		if g.installed: kinds.installed += 1
		if g.art.has("grid"): kinds.with_grid += 1
		if g.art.has("hero"): kinds.with_hero += 1
	var bridge_status := Shell.bridge.status.duplicate(true)
	return {
		"shell_version": ProjectSettings.get_setting("application/config/version"),
		"time": Time.get_datetime_string_from_system(),
		"system": SystemInfo.summary(),
		"battery": SystemInfo.battery(),
		"env": env,
		"steam_root": lib.steam_root, "account_id_present": lib.account_id != "",
		"library_paths": Array(SteamLibrary.library_paths(lib.steam_root)) if lib.steam_root != "" else [],
		"library_counts": kinds, "library_errors": Array(lib.errors), "library_scan": lib.scan,
		"games": Shell.games.map(func(g): return {"id": g.id, "name": g.name, "installed": g.installed,
			"flags": g.get("state_flags", 0), "last_played": g.last_played, "library": g.library,
			"art": g.art.keys()}),
		"runner": {"state": Shell.runner.state, "running_appid": Shell.runner.running_appid,
			"last_launch_cmd": Array(Shell.runner._last_launch_cmd)},
		"bridge": {"connected": Shell.bridge.connected, "last_error": Shell.bridge.last_error, "status": bridge_status},
		"joypads": Input.get_connected_joypads().map(func(i): return {"id": i, "name": Input.get_joy_name(i), "guid": Input.get_joy_guid(i)}),
		"screen": {"size": DisplayServer.screen_get_size(), "refresh": DisplayServer.screen_get_refresh_rate(),
			"window": DisplayServer.window_get_size(), "fps": Engine.get_frames_per_second(), "max_fps": Engine.max_fps},
		"running_appids": GameRunner.scan_running_appids(),
	}


## Writes the zip; returns its path or "" on failure.
static func write_package(dest_dir: String = "") -> String:
	if dest_dir == "":
		dest_dir = OS.get_environment("HOME") + "/Desktop"
		if not DirAccess.dir_exists_absolute(dest_dir):
			dest_dir = OS.get_environment("HOME")
	var path := dest_dir + "/gfg-shell-diag-%s.zip" % Time.get_datetime_string_from_system().replace(":", "-")
	var zip := ZIPPacker.new()
	if zip.open(path) != OK:
		Log.error("diag", "cannot write " + path)
		return ""
	_add(zip, "summary.json", JSON.stringify(collect(), "  "))
	_add(zip, "processes.txt", _run("sh", ["-c", "ps -eo pid,ppid,user,etimes,args --sort=pid | grep -Ei 'steam|gamescope|reaper|gfg|inputplumber|godot|mangoapp' | grep -v grep"]))
	_add(zip, "gamescope-atoms.txt", _run("sh", ["-c", "command -v xprop >/dev/null && for d in :0 :1; do echo \"== DISPLAY $d\"; DISPLAY=$d xprop -root | grep -E 'GAMESCOPE|STEAM' ; done || echo 'xprop not available'"]))
	_add(zip, "session.txt", _run("sh", ["-c", "cat /etc/os-release; echo; loginctl show-session $XDG_SESSION_ID 2>/dev/null; echo; systemctl --user --no-pager list-units 'gamescope*' 'steam*' 'gfg*' 2>/dev/null; ls -la /etc/sddm.conf.d 2>/dev/null"]))
	_add(zip, "input.txt", _run("sh", ["-c", "ls -la /dev/input/ 2>/dev/null; echo; cat /proc/bus/input/devices 2>/dev/null | grep -E '^(N|H):'; echo; systemctl is-active inputplumber 2>/dev/null"]))
	var dir := DirAccess.open(Log.log_dir)
	if dir != null:
		for f in dir.get_files():
			if f.ends_with(".log"):
				_add(zip, "logs/" + f, FileAccess.get_file_as_string(Log.log_dir + "/" + f))
	zip.close()
	Log.info("diag", "package written: " + path)
	return path


static func _add(zip: ZIPPacker, name: String, text: String) -> void:
	zip.start_file(name)
	zip.write_file(text.to_utf8_buffer())
	zip.close_file()
