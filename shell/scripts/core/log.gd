## Shell log: one plain-text file per run under ~/.local/share/gfg-shell/logs/, newest 10 kept.
## Every adapter decision (launch, detect, focus, bridge) is logged so a device log alone
## can show what happened. Static, so core scripts work in headless tests without autoloads.
class_name Log
extends RefCounted

const KEEP := 10
static var log_dir := ""
static var path := ""
static var lines: PackedStringArray = PackedStringArray()   # tail for diagnostics
static var _file: FileAccess
static var _opened := false


static func _open() -> void:
	_opened = true
	log_dir = OS.get_environment("GFG_SHELL_LOG_DIR")
	if log_dir == "":
		var base := OS.get_environment("XDG_DATA_HOME")
		if base == "":
			base = OS.get_environment("HOME") + "/.local/share"
		log_dir = base + "/gfg-shell/logs"
	DirAccess.make_dir_recursive_absolute(log_dir)
	var dir := DirAccess.open(log_dir)
	if dir != null:
		var files := Array(dir.get_files()).filter(func(f): return f.begins_with("shell-") and f.ends_with(".log"))
		files.sort()
		while files.size() >= KEEP:
			DirAccess.remove_absolute(log_dir + "/" + files.pop_front())
	path = log_dir + "/shell-%s.log" % Time.get_datetime_string_from_system().replace(":", "-")
	_file = FileAccess.open(path, FileAccess.WRITE)
	_write("I", "log", "GFG Shell %s, Godot %s, %s" % [ProjectSettings.get_setting("application/config/version"),
		Engine.get_version_info().string, OS.get_name()])


static func _write(level: String, area: String, msg: String) -> void:
	if not _opened:
		_open()
	var line := "%s %s [%s] %s" % [Time.get_time_string_from_system(), level, area, msg]
	lines.append(line)
	if lines.size() > 400:
		lines = lines.slice(lines.size() - 400)
	if _file != null:
		_file.store_line(line)
		_file.flush()
	if OS.get_environment("GFG_SHELL_LOG_STDOUT") == "1":
		print(line)


static func info(area: String, msg: String) -> void:
	_write("I", area, msg)


static func warn(area: String, msg: String) -> void:
	_write("W", area, msg)


static func error(area: String, msg: String) -> void:
	_write("E", area, msg)
