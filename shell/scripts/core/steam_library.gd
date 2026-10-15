## Steam Adapter — library side. Reads only files Steam itself writes; never edits them.
##   steamapps/libraryfolders.vdf, steamapps/appmanifest_*.acf    installed Steam apps
##   config/loginusers.vdf                                        which account is active
##   userdata/<account>/config/localconfig.vdf                    LastPlayed / Playtime
##   userdata/<account>/config/shortcuts.vdf (binary)             non-Steam games
##   userdata/<account>/config/grid/                              custom artwork
##   appcache/librarycache/                                       Steam artwork (old flat + per-app dirs)
##   userdata/<account>/config/cloudstorage/cloud-storage-namespace-1.json   Steam favorites (read-only)
## Every reader is tolerant: a missing or corrupt file yields fewer games, never a crash.
class_name SteamLibrary
extends RefCounted

const STEAMID64_BASE := 76561197960265728

## Runtime/tool depots that show up as installed apps but are not games.
## Only ids that are certainly not games (Steamworks redistributables, Steam Linux
## Runtimes, Proton Experimental); every other tool is recognised by its name.
const TOOL_APPIDS := [228980, 1070560, 1391110, 1628350, 1493710]
const TOOL_NAME_PREFIXES := ["Proton", "Steam Linux Runtime", "Steamworks Common", "SteamVR", "Steam Audio"]

var steam_root: String = ""
var account_id: String = ""
var games: Array = []          # Array[Dictionary], see _game()
var errors: PackedStringArray = PackedStringArray()
## Per library: {path, exists, manifests, games, tools, bad, duplicates} (diagnostics + Settings)
var scan: Array = []


static func find_steam_root(home: String = "") -> String:
	var env := OS.get_environment("GFG_SHELL_STEAM_ROOT")
	if env != "":
		return env
	if home == "":
		home = OS.get_environment("HOME")
	for c in [home + "/.local/share/Steam", home + "/.steam/steam", home + "/.steam/root"]:
		if DirAccess.dir_exists_absolute(c + "/steamapps"):
			return c
	return ""


static func read_text(path: String) -> String:
	if not FileAccess.file_exists(path):
		return ""
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return ""
	return f.get_as_text()


func load_library(root: String = "") -> Array:
	steam_root = root if root != "" else find_steam_root()
	games.clear()
	errors.clear()
	scan.clear()
	if steam_root == "":
		errors.append("steam-root-not-found")
		return games
	account_id = active_account_id(steam_root)
	var activity := _read_activity()
	var favorites := _read_steam_favorites()
	var seen := {}
	for lib in library_paths(steam_root):
		var report := {"path": lib, "exists": DirAccess.dir_exists_absolute(lib + "/steamapps"),
			"manifests": 0, "games": 0, "tools": 0, "bad": 0, "duplicates": 0}
		for g in _read_manifests(lib, report):
			if seen.has(g.id):
				report.duplicates += 1
				continue
			seen[g.id] = true
			report.games += 1
			games.append(g)
		scan.append(report)
	for g in _read_shortcuts():
		games.append(g)
	for g in games:
		# Steam writes LastPlayed both in the manifest and in localconfig; either may be
		# missing or stale, so the newer one wins (non-Steam shortcuts use the same key).
		var a: Dictionary = activity.get(str(g.appid), {})
		g.last_played = max(int(g.last_played), int(a.get("last_played", 0)))
		g.playtime_min = max(int(g.playtime_min), int(a.get("playtime_min", 0)))
		g.steam_favorite = favorites.has(int(g.appid))
		g.art = resolve_art(g)
	games.sort_custom(func(x, y): return x.name.naturalnocasecmp_to(y.name) < 0)
	return games


static func library_paths(root: String) -> PackedStringArray:
	var out := PackedStringArray([root])
	var d := Vdf.parse_text(read_text(root + "/steamapps/libraryfolders.vdf"))
	var top: Variant = Vdf.get_ci(d, "libraryfolders", {})
	if top is Dictionary:
		for k in top.keys():
			var entry: Variant = top[k]
			var p := ""
			if entry is Dictionary:
				p = str(Vdf.get_ci(entry, "path", ""))
			elif entry is String and str(k).is_valid_int():  # legacy format: "1" "/path"
				p = entry
			if p != "" and not out.has(p) and p.simplify_path() != root.simplify_path():
				out.append(p)
	return out


static func active_account_id(root: String) -> String:
	var env := OS.get_environment("GFG_SHELL_STEAM_ACCOUNT")
	if env != "":
		return env
	var d := Vdf.parse_text(read_text(root + "/config/loginusers.vdf"))
	var users: Variant = Vdf.get_ci(d, "users", {})
	var best := ""
	var best_ts := -1
	if users is Dictionary:
		for sid in users.keys():
			var u: Variant = users[sid]
			if not (u is Dictionary) or not str(sid).is_valid_int():
				continue
			var ts := int(str(Vdf.get_ci(u, "Timestamp", "0")))
			if str(Vdf.get_ci(u, "MostRecent", "0")) == "1":
				ts += 1 << 40
			if ts > best_ts:
				best_ts = ts
				best = str(int(str(sid)) - STEAMID64_BASE)
	if best == "":  # fall back to the only/first userdata folder
		var dir := DirAccess.open(root + "/userdata")
		if dir != null:
			for n in dir.get_directories():
				if n.is_valid_int() and n != "0":
					return n
	return best


## Display name and avatar of the active account (Steam menu header).
func persona() -> Dictionary:
	var out := {"name": "", "avatar": ""}
	if steam_root == "" or account_id == "" or not account_id.is_valid_int():
		return out
	var sid := str(int(account_id) + STEAMID64_BASE)
	var d := Vdf.parse_text(read_text(steam_root + "/config/loginusers.vdf"))
	var u: Variant = Vdf.get_path_ci(d, ["users", sid], {})
	if u is Dictionary:
		out.name = str(Vdf.get_ci(u, "PersonaName", ""))
	for f in [steam_root + "/config/avatarcache/" + sid + ".png"]:
		if FileAccess.file_exists(f):
			out.avatar = f
	return out


static func _game() -> Dictionary:
	return {"id": "", "appid": 0, "kind": "steam", "name": "", "installed": false,
		"state_flags": 0, "size_bytes": 0, "last_played": 0, "playtime_min": 0,
		"library": "", "install_dir": "", "exe": "", "launch_options": "", "launch_id": "",
		"steam_favorite": false, "art": {}, "bytes_to_download": 0, "bytes_downloaded": 0,
		"update_pending": false, "downloading": false}


static func is_tool_app(appid: int, name: String) -> bool:
	if TOOL_APPIDS.has(appid):
		return true
	for p in TOOL_NAME_PREFIXES:
		if name.begins_with(p):
			return true
	return false


static func parse_manifest(text: String, library: String) -> Dictionary:
	var d := Vdf.parse_text(text)
	var st: Variant = Vdf.get_ci(d, "AppState")
	if not (st is Dictionary):
		return {}
	var appid := int(str(Vdf.get_ci(st, "appid", "0")))
	var name := str(Vdf.get_ci(st, "name", ""))
	if appid <= 0 or name == "":
		return {}
	var g := _game()
	g.id = str(appid)
	g.appid = appid
	g.name = name
	g.state_flags = int(str(Vdf.get_ci(st, "StateFlags", "0")))
	# StateFlags bit 2 (value 4) = "fully installed"; updates/downloads set other bits on top.
	g.installed = (g.state_flags & 4) != 0
	var installdir := str(Vdf.get_ci(st, "installdir", ""))
	g.size_bytes = int(str(Vdf.get_ci(st, "SizeOnDisk", "0")))
	g.library = library
	g.install_dir = library + "/steamapps/common/" + installdir
	# an update or validation can clear the "fully installed" bit while the game is on disk
	if not g.installed and installdir != "" and int(g.size_bytes) > 0 and DirAccess.dir_exists_absolute(g.install_dir):
		g.installed = true
	g.last_played = int(str(Vdf.get_ci(st, "LastPlayed", "0")))
	g.launch_id = str(appid)
	# Download / update progress as Steam records it (Загрузки screen).
	g.bytes_to_download = int(str(Vdf.get_ci(st, "BytesToDownload", "0")))
	g.bytes_downloaded = int(str(Vdf.get_ci(st, "BytesDownloaded", "0")))
	g.update_pending = (g.state_flags & 2) != 0 or (g.state_flags & 1024) != 0 \
		or (g.bytes_to_download > 0 and g.bytes_downloaded < g.bytes_to_download)
	g.downloading = (g.state_flags & 1024) != 0
	return g


func _read_manifests(library: String, report: Dictionary = {}) -> Array:
	var out := []
	var dir := DirAccess.open(library + "/steamapps")
	if dir == null:
		return out
	for f in dir.get_files():
		if not (f.begins_with("appmanifest_") and f.ends_with(".acf")):
			continue
		report["manifests"] = int(report.get("manifests", 0)) + 1
		var g := parse_manifest(read_text(library + "/steamapps/" + f), library)
		if g.is_empty():
			errors.append("bad-manifest:" + f)
			report["bad"] = int(report.get("bad", 0)) + 1
			continue
		if is_tool_app(g.appid, g.name):
			report["tools"] = int(report.get("tools", 0)) + 1
			continue
		out.append(g)
	return out


func _userdata(rel: String) -> String:
	return steam_root + "/userdata/" + account_id + "/" + rel


## {appid: {last_played, playtime_min}} from localconfig.vdf.
func _read_activity() -> Dictionary:
	var out := {}
	if account_id == "":
		return out
	var d := Vdf.parse_text(read_text(_userdata("config/localconfig.vdf")))
	var apps: Variant = Vdf.get_path_ci(d, ["UserLocalConfigStore", "Software", "Valve", "Steam", "apps"], {})
	if apps is Dictionary:
		for k in apps.keys():
			var a: Variant = apps[k]
			if a is Dictionary:
				out[str(k)] = {"last_played": int(str(Vdf.get_ci(a, "LastPlayed", "0"))),
					"playtime_min": int(str(Vdf.get_ci(a, "Playtime", "0")))}
	return out


## Steam's own Favorites collection, if the client stored it locally (read-only; GFG keeps its own toggles).
func _read_steam_favorites() -> Dictionary:
	var out := {}
	if account_id == "":
		return out
	var raw := read_text(_userdata("config/cloudstorage/cloud-storage-namespace-1.json"))
	if raw == "":
		return out
	var parsed: Variant = JSON.parse_string(raw)
	if not (parsed is Array):
		return out
	for entry in parsed:
		if entry is Array and entry.size() >= 2 and str(entry[0]) == "user-collections.favorite":
			var meta: Variant = entry[1]
			if meta is Dictionary and meta.get("value") is String:
				var col: Variant = JSON.parse_string(meta["value"])
				if col is Dictionary and col.get("added") is Array:
					for a in col["added"]:
						out[int(a)] = true
	return out


## 64-bit Steam game id for a non-Steam shortcut: (appid << 32) | 0x02000000, as unsigned decimal.
static func shortcut_game_id(appid32: int) -> String:
	var u := appid32 & 0xFFFFFFFF
	# u * 2^32 + 0x02000000 overflows int64 for u >= 2^31; do it in base 10^9 limbs.
	var limbs := [u]  # little-endian base 1e9
	for _i in 32:
		var carry := 0
		for j in limbs.size():
			var v: int = limbs[j] * 2 + carry
			limbs[j] = v % 1000000000
			carry = v / 1000000000
		if carry > 0:
			limbs.append(carry)
	var add := 0x02000000
	var j2 := 0
	while add > 0:
		if j2 >= limbs.size():
			limbs.append(0)
		var v2: int = limbs[j2] + add
		limbs[j2] = v2 % 1000000000
		add = v2 / 1000000000
		j2 += 1
	var s := str(limbs[limbs.size() - 1])
	for k in range(limbs.size() - 2, -1, -1):
		s += "%09d" % limbs[k]
	return s


static func parse_shortcuts(data: PackedByteArray) -> Array:
	var out := []
	var d := Vdf.parse_binary(data)
	var list: Variant = Vdf.get_ci(d, "shortcuts", {})
	if not (list is Dictionary):
		return out
	for k in list.keys():
		var s: Variant = list[k]
		if not (s is Dictionary):
			continue
		var name := str(Vdf.get_ci(s, "AppName", Vdf.get_ci(s, "appname", "")))
		var appid := int(Vdf.get_ci(s, "appid", 0)) & 0xFFFFFFFF
		if name == "" or appid == 0:
			continue
		if int(Vdf.get_ci(s, "IsHidden", 0)) != 0:
			continue
		var g := _game()
		g.kind = "shortcut"
		g.appid = appid
		g.id = "s" + str(appid)
		g.name = name
		g.installed = true
		g.exe = str(Vdf.get_ci(s, "Exe", ""))
		g.launch_options = str(Vdf.get_ci(s, "LaunchOptions", ""))
		g.last_played = int(Vdf.get_ci(s, "LastPlayTime", 0))
		g.launch_id = shortcut_game_id(appid)
		g.icon_path = str(Vdf.get_ci(s, "icon", ""))
		out.append(g)
	return out


func _read_shortcuts() -> Array:
	if account_id == "":
		return []
	var path := _userdata("config/shortcuts.vdf")
	if not FileAccess.file_exists(path):
		return []
	var data := FileAccess.get_file_as_bytes(path)
	var out := parse_shortcuts(data)
	# The shell itself is (in stage B) a non-Steam shortcut: hide it from its own library.
	return out.filter(func(g): return not str(g.exe).contains("gfg-shell"))


## Artwork lookup: custom grid first, then Steam's cache (flat legacy names, then per-app directories).
func resolve_art(g: Dictionary) -> Dictionary:
	var art := {}
	var id := str(g.appid)
	var grid := _userdata("config/grid/")
	var custom := {"grid": id + "p", "hero": id + "_hero", "logo": id + "_logo", "header": id}
	for slot in custom.keys():
		for ext in [".png", ".jpg", ".jpeg", ".webp"]:
			if account_id != "" and FileAccess.file_exists(grid + custom[slot] + ext):
				art[slot] = grid + custom[slot] + ext
				break
	if g.kind == "steam":
		var cache := steam_root + "/appcache/librarycache/"
		var flat := {"grid": id + "_library_600x900.jpg", "hero": id + "_library_hero.jpg",
			"logo": id + "_logo.png", "header": id + "_header.jpg"}
		for slot in flat.keys():
			if not art.has(slot) and FileAccess.file_exists(cache + flat[slot]):
				art[slot] = cache + flat[slot]
		if DirAccess.dir_exists_absolute(cache + id):
			var found := {}
			_scan_art_dir(cache + id, found, 0)
			for slot in found.keys():
				if not art.has(slot):
					art[slot] = found[slot]
	elif g.get("icon_path", "") != "" and FileAccess.file_exists(g.icon_path):
		art["icon"] = g.icon_path
	return art


static func _scan_art_dir(path: String, found: Dictionary, depth: int) -> void:
	var dir := DirAccess.open(path)
	if dir == null or depth > 2:
		return
	for f in dir.get_files():
		var l := f.to_lower()
		var slot := ""
		if l.begins_with("library_600x900") or l.begins_with("library_capsule"):
			slot = "grid"
		elif l.begins_with("library_hero") and not l.contains("blur"):
			slot = "hero"
		elif l.begins_with("logo"):
			slot = "logo"
		elif l.begins_with("header"):
			slot = "header"
		if slot != "" and not found.has(slot):
			found[slot] = path + "/" + f
	for d in dir.get_directories():
		_scan_art_dir(path + "/" + d, found, depth + 1)
