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


static func volume_pct() -> int:
	var out := []
	if OS.execute("wpctl", ["get-volume", "@DEFAULT_AUDIO_SINK@"], out) != 0 or out.is_empty():
		return -1
	var parts := (out[0] as String).split(" ", false)  # "Volume: 0.45 [MUTED]"
	if parts.size() >= 2 and parts[1].is_valid_float():
		return int(round(float(parts[1]) * 100.0))
	return -1


static func change_volume(step_pct: int) -> void:
	var arg := "%d%%%s" % [abs(step_pct), "+" if step_pct > 0 else "-"]
	OS.execute("wpctl", ["set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", arg], [])


## action: suspend | reboot | poweroff. Goes through logind like the stock power menu.
static func power(action: String) -> int:
	if not action in ["suspend", "reboot", "poweroff"]:
		return -1
	Log.info("power", action)
	if OS.get_environment("GFG_SHELL_DRY_POWER") == "1":
		return 0
	return OS.execute("systemctl", [action], [])
