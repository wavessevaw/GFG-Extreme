## Device facts and power actions. Read-only sysfs, plus the same user-level commands
## SteamOS itself offers (systemctl suspend/reboot/poweroff via logind, wpctl volume).
## Brightness stays with Steam/gamescope in this stage: it is read, not written.
class_name SystemInfo
extends RefCounted

static var _sys_root := ""


static func sys_root() -> String:
	if _sys_root == "":
		_sys_root = OS.get_environment("GFG_SHELL_SYS_ROOT")
		if _sys_root == "":
			_sys_root = "/sys"
	return _sys_root


static func _read(path: String) -> String:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return ""
	return f.get_buffer(4096).get_string_from_utf8().strip_edges()


static func battery() -> Dictionary:
	var dir := DirAccess.open(sys_root() + "/class/power_supply")
	if dir == null:
		return {"available": false}
	for n in dir.get_directories() + dir.get_files():
		var base := sys_root() + "/class/power_supply/" + n
		if _read(base + "/type") == "Battery":
			var cap := _read(base + "/capacity")
			var st := _read(base + "/status")
			return {"available": cap.is_valid_int(), "percent": int(cap) if cap.is_valid_int() else -1,
				"charging": st == "Charging" or st == "Full", "status": st}
	return {"available": false}


static func brightness_pct() -> int:
	var dir := DirAccess.open(sys_root() + "/class/backlight")
	if dir == null:
		return -1
	for n in dir.get_directories() + dir.get_files():
		var b := _read(sys_root() + "/class/backlight/" + n + "/brightness")
		var m := _read(sys_root() + "/class/backlight/" + n + "/max_brightness")
		if b.is_valid_int() and m.is_valid_int() and int(m) > 0:
			return int(round(100.0 * int(b) / int(m)))
	return -1


static func network() -> Dictionary:
	var dir := DirAccess.open(sys_root() + "/class/net")
	if dir == null:
		return {"online": false}
	for n in dir.get_directories() + dir.get_files():
		if n == "lo":
			continue
		if _read(sys_root() + "/class/net/" + n + "/operstate") == "up":
			return {"online": true, "iface": n, "wifi": n.begins_with("wl")}
	return {"online": false}


static func os_release() -> Dictionary:
	var out := {}
	for line in FileAccess.get_file_as_string("/etc/os-release").split("\n"):
		var i := line.find("=")
		if i > 0:
			out[line.substr(0, i)] = line.substr(i + 1).trim_prefix("\"").trim_suffix("\"")
	return out


static func device_model() -> String:
	var name := _read(sys_root() + "/class/dmi/id/product_name")
	var board := _read(sys_root() + "/class/dmi/id/board_name")
	# Jupiter = Steam Deck LCD, Galileo = Steam Deck OLED.
	if name == "Galileo":
		return "Steam Deck OLED"
	if name == "Jupiter":
		return "Steam Deck LCD"
	return name if name != "" else (board if board != "" else "unknown")


static func summary() -> Dictionary:
	var osr := os_release()
	var out := []
	OS.execute("uname", ["-r"], out)
	var mem := ""
	for line in FileAccess.get_file_as_string("/proc/meminfo").split("\n"):
		if line.begins_with("MemTotal:"):
			mem = "%.1f ГБ" % (float(line.split(" ", false)[1]) / 1048576.0)
	return {"device": device_model(), "os": osr.get("PRETTY_NAME", OS.get_distribution_name()),
		"os_version": osr.get("VERSION_ID", ""), "build": osr.get("BUILD_ID", ""),
		"kernel": (out[0] as String).strip_edges() if out.size() > 0 else "", "memory": mem,
		"cpu": OS.get_processor_name(), "gpu": RenderingServer.get_video_adapter_name(),
		"godot": Engine.get_version_info().string}


## Audio goes through PipeWire's own tools. Steam starts the Shell with its runtime's
## LD_LIBRARY_PATH / LD_PRELOAD (overlay), which can break system binaries, so they run
## under `env -u` with a clean library path. wpctl first, pactl (pipewire-pulse) as fallback.
static var _audio_tool := ""


static func _audio(tool: String, args: Array, out: Array = []) -> int:
	var full := ["-u", "LD_PRELOAD", "-u", "LD_LIBRARY_PATH", tool] + args
	var code := OS.execute("/usr/bin/env", PackedStringArray(full), out, true)
	if code != 0:
		Log.info("audio", "%s %s -> exit %d %s" % [tool, " ".join(args), code,
			str(out[0]).strip_edges().left(160) if out.size() > 0 else ""])
	return code


## wpctl prints "Volume: 0.45 [MUTED]"; pactl prints "... / 45% / ..." per channel.
static func parse_volume(tool: String, text: String) -> int:
	# stderr is mixed in (ld.so warnings about Steam's overlay preload): find the value line
	if tool == "wpctl":
		for line in text.split("\n"):
			var parts := line.strip_edges().split(" ", false)
			if parts.size() >= 2 and parts[0] == "Volume:" and parts[1].is_valid_float():
				return clampi(int(round(float(parts[1]) * 100.0)), 0, 150)
		return -1
	var re := RegEx.create_from_string("(\\d+)%")
	var m := re.search(text)
	return clampi(int(m.get_string(1)), 0, 150) if m != null else -1


static func volume_pct() -> int:
	for tool in ([_audio_tool] if _audio_tool != "" else ["wpctl", "pactl"]):
		var out := []
		var args := ["get-volume", "@DEFAULT_AUDIO_SINK@"] if tool == "wpctl" else ["get-sink-volume", "@DEFAULT_SINK@"]
		if _audio(tool, args, out) == 0 and not out.is_empty():
			var v := parse_volume(tool, str(out[0]))
			if v >= 0:
				_audio_tool = tool
				return v
	_audio_tool = ""
	return -1


static func set_volume_pct(pct: int) -> bool:
	pct = clampi(pct, 0, 100)
	var tools := [_audio_tool] if _audio_tool != "" else ["wpctl", "pactl"]
	for tool in tools:
		var ok := false
		if tool == "wpctl":
			var frac := "%.2f" % (pct / 100.0)
			ok = _audio("wpctl", ["set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", frac]) == 0 \
				or _audio("wpctl", ["set-volume", "@DEFAULT_AUDIO_SINK@", frac]) == 0  # wpctl before -l
			if ok and pct > 0:
				_audio("wpctl", ["set-mute", "@DEFAULT_AUDIO_SINK@", "0"])
		else:
			ok = _audio("pactl", ["set-sink-volume", "@DEFAULT_SINK@", "%d%%" % pct]) == 0
			if ok and pct > 0:
				_audio("pactl", ["set-sink-mute", "@DEFAULT_SINK@", "0"])
		if ok:
			_audio_tool = tool
			Log.info("audio", "volume %d%% via %s" % [pct, tool])
			return true
	Log.info("audio", "volume %d%%: no audio tool worked" % pct)
	return false


static func change_volume(step_pct: int) -> void:
	var v := volume_pct()
	if v >= 0:
		set_volume_pct(v + step_pct)


## action: suspend | reboot | poweroff. Goes through logind like the stock power menu.
static func power(action: String) -> int:
	if not action in ["suspend", "reboot", "poweroff"]:
		return -1
	Log.info("power", action)
	if OS.get_environment("GFG_SHELL_DRY_POWER") == "1":
		return 0
	return OS.execute("systemctl", [action], [])


static func _backlight_path() -> String:
	var dir := DirAccess.open(sys_root() + "/class/backlight")
	if dir == null:
		return ""
	for n in dir.get_directories() + dir.get_files():
		return sys_root() + "/class/backlight/" + n
	return ""


## Writes brightness the way SteamOS's own tools do (polkit helper steamos-priv-write);
## returns false when the helper is missing or refuses (then Steam keeps control).
static func set_brightness_pct(pct: int) -> bool:
	var base := _backlight_path()
	var helper := "/usr/bin/steamos-polkit-helpers/steamos-priv-write"
	if base == "" or not FileAccess.file_exists(helper):
		return false
	var m := _read(base + "/max_brightness")
	if not m.is_valid_int():
		return false
	var raw := int(round(int(m) * clampi(pct, 3, 100) / 100.0))
	var code := OS.execute(helper, [base + "/brightness", str(raw)], [])
	Log.info("system", "brightness %d%% -> %d (exit %d)" % [pct, raw, code])
	return code == 0


static func wifi_name() -> String:
	var out := []
	if OS.execute("nmcli", ["-t", "-f", "active,ssid", "dev", "wifi"], out) != 0 or out.is_empty():
		return ""
	for line in (out[0] as String).split("\n"):
		if line.begins_with("yes:"):
			return line.substr(4)
	return ""


## {total, free} bytes of the filesystem holding path (df -B1).
static func storage(path: String) -> Dictionary:
	var out := []
	if OS.execute("df", ["-B1", "--output=size,avail", path], out) != 0 or out.is_empty():
		return {}
	var lines := (out[0] as String).strip_edges().split("\n")
	if lines.size() < 2:
		return {}
	var parts := lines[1].split(" ", false)
	if parts.size() < 2 or not parts[0].is_valid_int():
		return {}
	return {"total": int(parts[0]), "free": int(parts[1])}
