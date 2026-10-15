## Headless tests: godot --headless --path shell -s res://tests/run_tests.gd -- --fixture=<dir>
## <dir> comes from tools/make_fake_steam.py. Exit code = number of failures.
extends SceneTree

var failures := 0
var checks := 0
var fixture := ""


func check(cond: bool, what: String) -> void:
	checks += 1
	if not cond:
		failures += 1
		printerr("FAIL: " + what)


func eq(a: Variant, b: Variant, what: String) -> void:
	check(a == b, "%s: got %s, want %s" % [what, str(a), str(b)])


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--fixture="):
			fixture = a.substr(10)
	test_vdf_text()
	test_vdf_binary_malformed()
	test_shortcut_id()
	test_cmdline()
	test_proc_scan()
	test_runner_lifecycle()
	test_install_launch()
	test_input_map()
	if fixture != "":
		test_appinfo()
		test_library()
		test_owned_library()
		test_corrupt_appinfo_library()
		test_state_queries()
	else:
		check(false, "--fixture=<dir> missing")
	print("%d checks, %d failures" % [checks, failures])
	quit(failures)


func test_vdf_text() -> void:
	var d := Vdf.parse_text('// comment\n"Root"\n{\n\t"a"\t\t"1"\n\t"Esc"\t"x\\"y\\\\z"\n\tbare value\n\t"Sub" { "K" "v" }\n\t"empty" {}\n}\n')
	var r: Dictionary = d.get("Root", {})
	eq(r.get("a"), "1", "vdf simple")
	eq(r.get("Esc"), "x\"y\\z", "vdf escapes")
	eq(r.get("bare"), "value", "vdf unquoted")
	eq(Vdf.get_path_ci(d, ["root", "sub", "k"]), "v", "vdf case-insensitive path")
	eq(r.get("empty"), {}, "vdf empty block")
	eq(Vdf.parse_text(""), {}, "vdf empty input")
	eq(Vdf.parse_text('"a" { "b" "c"').get("a", {}).get("b"), "c", "vdf unterminated block tolerated")


func test_vdf_binary_malformed() -> void:
	eq(Vdf.parse_binary(PackedByteArray()), {}, "bin empty")
	eq(Vdf.parse_binary(PackedByteArray([0x00, 0x73, 0x00, 0x02, 0x61, 0x00, 0x01])), {}, "bin truncated int")
	eq(Vdf.parse_binary(PackedByteArray([0x09, 0x61, 0x00])), {}, "bin unknown type")
	var ok := PackedByteArray([0x00]) + "m".to_utf8_buffer() + PackedByteArray([0, 0x01]) + "k".to_utf8_buffer() + PackedByteArray([0]) + "v".to_utf8_buffer() + PackedByteArray([0, 0x08, 0x08])
	eq(Vdf.parse_binary(ok), {"m": {"k": "v"}}, "bin nested string")
	# a file cut inside its second entry keeps the first one
	var two := PackedByteArray([0x00]) + "s".to_utf8_buffer() + PackedByteArray([0, 0x00, 0x30, 0, 0x01]) \
		+ "AppName".to_utf8_buffer() + PackedByteArray([0]) + "A".to_utf8_buffer() + PackedByteArray([0, 0x08, 0x00, 0x31, 0, 0x01]) \
		+ "AppName".to_utf8_buffer() + PackedByteArray([0]) + "B".to_utf8_buffer()
	eq(Vdf.parse_binary(two), {"s": {"0": {"AppName": "A"}}}, "bin truncated: complete entries kept")
	# pointer/color (4 bytes) and the 0x0B end marker some writers use
	var odd := PackedByteArray([0x04]) + "p".to_utf8_buffer() + PackedByteArray([0, 1, 0, 0, 0, 0x06]) + "c".to_utf8_buffer() \
		+ PackedByteArray([0, 2, 0, 0, 0, 0x01]) + "k".to_utf8_buffer() + PackedByteArray([0]) + "v".to_utf8_buffer() + PackedByteArray([0, 0x0B])
	eq(Vdf.parse_binary(odd), {"p": 1, "c": 2, "k": "v"}, "bin pointer/color/0x0B")
	eq(Vdf.parse_text('"a" "x\\\\y" "b" "tail\\').get("a"), "x\\y", "vdf backslash then unterminated tail")
	eq(Vdf.parse_text('\uFEFF"A" { "k" "v" }').size() > 0, true, "vdf with BOM does not crash")
	eq(SteamLibrary.read_text(fixture + "/nope.vdf"), "", "read_text missing")


func test_shortcut_id() -> void:
	eq(SteamLibrary.shortcut_game_id(-1820446516), "10627985823405965312", "shortcut id with sign bit")
	eq(SteamLibrary.shortcut_game_id(2081234567), "8938834400603275264", "shortcut id positive")
	eq(SteamLibrary.crc32("123456789".to_utf8_buffer()), 0xCBF43926, "crc32 check value")
	eq(SteamLibrary.legacy_shortcut_appid('"/home/deck/Games/old/start.sh"', "Old Shortcut"), 3267396389, "legacy shortcut id")


func _cmd(parts: Array) -> PackedByteArray:
	var b := PackedByteArray()
	for p in parts:
		b.append_array(str(p).to_utf8_buffer())
		b.append(0)
	return b


func test_cmdline() -> void:
	eq(GameRunner.parse_steamlaunch_cmdline(_cmd(["/steam/reaper", "SteamLaunch", "AppId=4100010", "--", "/x/proton", "run", "game.exe"])), 4100010, "reaper cmdline")
	eq(GameRunner.parse_steamlaunch_cmdline(_cmd(["reaper", "SteamLaunch", "AppId=-1820446516", "--", "sh"])), 2474520780, "shortcut appid unsigned")
	eq(GameRunner.parse_steamlaunch_cmdline(_cmd(["game.exe", "--", "SteamLaunch", "AppId=5"])), 0, "marker after -- ignored")
	eq(GameRunner.parse_steamlaunch_cmdline(_cmd(["steam", "AppId=7"])), 0, "no marker")
	eq(GameRunner.parse_steamlaunch_cmdline(PackedByteArray()), 0, "empty cmdline")
	eq(GameRunner.launch_uri({"launch_id": "123"}), "steam://rungameid/123", "launch uri")
	check(GameRunner.needs_install({"kind": "steam", "appid": 5, "installed": false}), "uninstalled Steam game needs install")
	check(not GameRunner.needs_install({"kind": "shortcut", "appid": 5, "installed": false}), "shortcuts never install")
	check(not GameRunner.needs_install({"launch_id": "123"}), "unknown install state launches")
	eq(GameRunner.install_uri({"appid": 4100110}), "steam://install/4100110", "install uri")


func test_proc_scan() -> void:
	var root := OS.get_cache_dir() + "/gfg-shell-test-proc-%d" % OS.get_process_id()
	for p in [["100", ["bash"]], ["200", ["reaper", "SteamLaunch", "AppId=4100020", "--", "wine"]], ["201", ["wine", "x.exe"]], ["self", ["x"]]]:
		DirAccess.make_dir_recursive_absolute(root + "/" + p[0])
		var f := FileAccess.open(root + "/" + p[0] + "/cmdline", FileAccess.WRITE)
		f.store_buffer(_cmd(p[1]))
		f.close()
	eq(GameRunner.scan_running_appids(root), [4100020], "proc scan finds reaper")
	eq(GameRunner.scan_running_appids(root + "/missing"), [], "proc scan missing root")
	# real /proc: must not crash and must read non-empty cmdlines despite length 0
	var mine := FileAccess.open("/proc/self/cmdline", FileAccess.READ)
	check(mine != null and not mine.get_buffer(8192).is_empty(), "read /proc/self/cmdline")
	OS.execute("rm", ["-rf", root])


func test_library() -> void:
	var lib := SteamLibrary.new()
	var games := lib.load_library(fixture + "/Steam")
	eq(lib.account_id, "39734314", "active account from MostRecent")
	eq(SteamLibrary.library_paths(fixture + "/Steam").size(), 2, "two libraries")
	var by := {}
	for g in games:
		by[g.name] = g
	eq(games.size(), 17, "11 installed-manifest games + 3 owned + 3 shortcuts (tool, broken manifest, shell hidden)")
	check(not by.has("Proton Experimental"), "Proton hidden")
	check(not by.has("GFG Shell"), "shell hides itself")
	check(lib.errors.has("bad-manifest:appmanifest_9999.acf"), "truncated manifest reported")
	eq(games.filter(func(g): return g.installed).size(), 13, "installed count (StateFlags bit 4)")
	check(not by["Glass Cathedral"].installed, "StateFlags 2 is not installed")
	check(by["Hollow Lantern"].installed, "StateFlags 6 (update) still installed")
	eq(by["Пепел Севера"].library, fixture + "/sdcard", "game in second library")
	eq(by["Neon Drift"].playtime_min, 1260, "playtime from localconfig (Apps key case)")
	check(by["Neon Drift"].last_played > 0, "last played")
	check(by["Пепел Севера"].steam_favorite and by["Tidebreaker"].steam_favorite, "Steam favorites read")
	check(not by["Neon Drift"].steam_favorite, "non-favorite")
	var rah: Dictionary = by["Retro Arcade Hub"]
	eq(rah.kind, "shortcut", "shortcut kind")
	eq(rah.launch_id, "10627985823405965312", "shortcut launch id")
	check(rah.last_played > 0, "shortcut LastPlayTime")
	check(str(rah.art.get("grid", "")).ends_with("2474520780p.png"), "shortcut custom grid art")
	check(str(by["Neon Drift"].art.get("grid", "")).ends_with("4100010_library_600x900.jpg"), "flat legacy art")
	check(str(by["Пепел Севера"].art.get("grid", "")).ends_with("4100020/a1b2c3d4e5/library_600x900.jpg"), "per-app hashed art")
	check(str(by["Пепел Севера"].art.get("hero", "")).ends_with("4100020/library_hero.jpg"), "per-app hero art")
	check(not by["Quiet Engine"].art.has("grid"), "no art -> placeholder")
	check(by["Sky Courier"].last_played > by["Neon Drift"].last_played, "manifest LastPlayed kept when localconfig lacks it")
	check(by["Hollow Lantern"].update_pending and by["Hollow Lantern"].bytes_downloaded == 5300000000, "update progress from manifest")
	check(not by["Neon Drift"].update_pending, "no update pending")
	eq(lib.scan.size(), 2, "scan report per library")
	eq(lib.scan[0].tools + lib.scan[1].tools, 1, "one tool skipped (Proton)")
	eq(lib.scan[0].bad + lib.scan[1].bad, 1, "one broken manifest reported")
	eq(lib.scan[0].games + lib.scan[1].games, 11, "11 Steam manifest games counted")
	eq(lib.scan[0].duplicates, 1, "stale duplicate manifest counted")
	check(not SteamLibrary.is_tool_app(1245040, "Some Game"), "unknown ids are not filtered as tools")
	check(SteamLibrary.is_tool_app(2805730, "Proton 9.0"), "tools recognised by name")
	check(SteamLibrary.is_tool_app(1, "Proton"), "bare tool name")
	check(not SteamLibrary.is_tool_app(1, "Protonaut"), "name prefix is a whole word")
	check(not SteamLibrary.is_tool_app(1, "Proton 9.0", "game"), "appinfo type decides over the name")
	check(SteamLibrary.is_tool_app(1, "Map Editor", "tool"), "appinfo type tool")
	check(not SteamLibrary.is_tool_app(1, "Wallpaper App", "application"), "installed applications stay")
	eq(SteamLibrary.new().load_library(fixture + "/nope"), [], "missing root yields empty library")


func test_appinfo() -> void:
	for v in [27, 28, 29]:
		var r := SteamAppInfo.new()
		var all := r.read(fixture + "/appinfo_v%d.vdf" % v)
		eq([r.version, r.error, all.size()], [v, "", 15], "appinfo v%d: every entry" % v)
		eq(all.get(4100110, {}), {"name": "Frost Signal", "type": "game"}, "appinfo v%d: name and type" % v)
		eq(all.get(4100120, {}).get("type"), "game", "appinfo v%d: type lower-cased" % v)
		eq(all.get(4100140, {}).get("type"), "dlc", "appinfo v%d: dlc" % v)
		var some := r.read(fixture + "/appinfo_v%d.vdf" % v, {4100150: true, 4100060: true, 777: true})
		eq(some.keys().size(), 2, "appinfo v%d: only wanted ids" % v)
		eq(some.get(4100150, {}).get("name"), "Foundry Map Editor", "appinfo v%d: wanted entry" % v)
	var r2 := SteamAppInfo.new()
	eq(r2.read(fixture + "/appinfo_truncated.vdf"), {}, "appinfo v29 without string table: nothing")
	check(r2.error != "", "appinfo truncated v29 reported")
	eq(r2.read(fixture + "/missing.vdf"), {}, "appinfo missing file")
	eq(r2.error, "missing", "appinfo missing reported")
	var tmp := OS.get_cache_dir() + "/gfg-shell-test-appinfo-%d.vdf" % OS.get_process_id()
	var v28 := FileAccess.get_file_as_bytes(fixture + "/appinfo_v28.vdf")
	for case in [["short", PackedByteArray([0x28, 0x44])], ["bad magic", PackedByteArray([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])],
			["v28 cut", v28.slice(0, v28.size() / 2)], ["v28 corrupt kv", _corrupt_first_kv(v28)],
			["v28 bad size", _bad_first_size(v28)]]:
		var f := FileAccess.open(tmp, FileAccess.WRITE)
		f.store_buffer(case[1])
		f.close()
		var r3 := SteamAppInfo.new()
		var got := r3.read(tmp)
		match case[0]:
			"short", "bad magic":
				eq(got, {}, "appinfo %s: nothing" % case[0])
				check(r3.error != "", "appinfo %s: error set" % case[0])
			"v28 cut":
				check(got.size() > 0 and got.size() < 15, "appinfo cut file: entries before the cut (%d)" % got.size())
				eq(r3.error, "truncated", "appinfo cut file reported")
			"v28 corrupt kv":
				check(not got.has(4100010) and got.size() == 14, "appinfo broken entry skipped, rest kept")
			"v28 bad size":
				eq(got, {}, "appinfo impossible size stops the walk")
	DirAccess.remove_absolute(tmp)


## v28 header is 8 bytes, entry header 68: the first KeyValues type byte is at 8 + 68.
func _corrupt_first_kv(b: PackedByteArray) -> PackedByteArray:
	var c := b.duplicate()
	c[8 + 68] = 0x09
	return c


func _bad_first_size(b: PackedByteArray) -> PackedByteArray:
	var c := b.duplicate()
	c.encode_u32(12, 0x7FFFFFF0)
	return c


func test_owned_library() -> void:
	var lib := SteamLibrary.new()
	var games := lib.load_library(fixture + "/Steam")
	var by := {}
	var ids := {}
	for g in games:
		by[g.name] = g
		ids[g.id] = int(ids.get(g.id, 0)) + 1
	check(ids.values().all(func(n): return n == 1), "every game listed once")
	for n in ["Frost Signal", "Lumen Tactics", "Paper Comet"]:
		check(by.has(n) and not by[n].installed and by[n].source == "owned", "owned uninstalled game listed: " + n)
	if by.has("Lumen Tactics"):
		eq(by["Lumen Tactics"].playtime_min, 640, "owned game keeps its playtime")
		eq(by["Lumen Tactics"].launch_id, "4100120", "owned game launch id")
	for n in ["Neon Drift Soundtrack", "Neon Drift: Night Pack", "Foundry Map Editor", "Frost Signal Demo",
			"Orbital Foundry Server", "Not Owned Game", "Hidden Relic", "Proton Experimental"]:
		check(not by.has(n), "not listed: " + n)
	check(by["Neon Drift"].installed and by["Neon Drift"].source == "manifest", "installed copy wins over appinfo")
	check(not by["Glass Cathedral"].installed and by["Glass Cathedral"].source == "manifest", "manifest copy wins even when not installed")
	check(by["Пепел Севера"].installed, "installed duplicate wins over a stale manifest")
	eq(by["Пепел Севера"].library, fixture + "/sdcard", "the installed copy's library")
	check(by.has("Protonaut") and by["Protonaut"].installed, "game whose name starts with Proton is listed")
	check(by.has("Ember Trail") and by["Ember Trail"].installed, "nameless manifest named from appinfo")
	check(by.has("Kite Valley"), "nameless manifest named from installdir")
	check(by.has("Old Shortcut") and by["Old Shortcut"].appid == 3267396389, "shortcut without appid gets Steam's legacy id")
	check(str(by.get("Frost Signal", {}).get("art", {}).get("grid", "")) == "" or by["Frost Signal"].art.grid.contains("4100110"), "owned game art from librarycache")
	eq(lib.owned_report.get("listed"), 3, "owned report")
	check([27, 28, 29].has(lib.owned_report.get("appinfo_version")), "appinfo version reported")


## A corrupt appinfo.vdf costs the owned games and appinfo names, never the installed ones.
func test_corrupt_appinfo_library() -> void:
	var tmp := OS.get_cache_dir() + "/gfg-shell-test-steam-%d" % OS.get_process_id()
	OS.execute("rm", ["-rf", tmp])
	DirAccess.make_dir_recursive_absolute(tmp)
	OS.execute("cp", ["-r", fixture + "/Steam", tmp + "/Steam"])
	var f := FileAccess.open(tmp + "/Steam/appcache/appinfo.vdf", FileAccess.WRITE)
	f.store_buffer(PackedByteArray([0x29, 0x44, 0x56, 0x07, 1, 0, 0, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x7F, 9, 9]))
	f.close()
	var lib := SteamLibrary.new()
	var games := lib.load_library(tmp + "/Steam")
	var names := games.map(func(g): return g.name)
	eq(games.filter(func(g): return g.installed).size(), 13, "corrupt appinfo: installed games all listed")
	check(not names.has("Frost Signal"), "corrupt appinfo: no owned games")
	check(names.has("EmberTrail"), "corrupt appinfo: nameless manifest falls back to installdir")
	check(not names.has("Proton Experimental"), "corrupt appinfo: tools still hidden by id/name")
	check(Array(lib.errors).any(func(e): return str(e).begins_with("appinfo:")), "corrupt appinfo reported")
	DirAccess.remove_absolute(tmp + "/Steam/appcache/appinfo.vdf")
	games = lib.load_library(tmp + "/Steam")
	eq(games.filter(func(g): return g.installed).size(), 13, "no appinfo: installed games all listed")
	check(not Array(lib.errors).any(func(e): return str(e).begins_with("appinfo:")), "missing appinfo is not an error")
	OS.execute("rm", ["-rf", tmp])


func test_state_queries() -> void:
	var shell: Node = root.get_node_or_null("Shell")
	check(shell != null, "Shell autoload present")
	if shell == null:
		return
	shell.games = shell.library.load_library(fixture + "/Steam")
	shell.favorites = {}
	var recent: Array = shell.recent_games(3)
	eq(recent.map(func(g): return g.name), ["Sky Courier", "Neon Drift", "Пепел Севера"], "recent order")
	eq(shell.favorite_games().size(), 2, "favorites from Steam")
	var nd: Dictionary = shell.games.filter(func(g): return g.name == "Neon Drift")[0]
	shell.favorites[nd.id] = true
	eq(shell.favorite_games().size(), 3, "GFG favorite added")
	var pep: Dictionary = shell.games.filter(func(g): return g.name == "Пепел Севера")[0]
	shell.favorites[pep.id] = false
	eq(shell.favorite_games().size(), 2, "GFG override removes Steam favorite")
	eq(shell.search("пеп").size(), 1, "cyrillic search")
	eq(shell.search("o")[0].name.to_lower().begins_with("o"), true, "prefix match first")
	eq(shell.filtered_games("nonsteam", "name").size(), 3, "non-Steam filter")
	eq(shell.filtered_games("installed", "name").size(), 13, "installed filter")
	check(shell.filtered_games("installed", "name").all(func(g): return g.installed), "installed filter has no owned-only games")
	eq(shell.filtered_games("all", "name").size(), 17, "all includes owned games")
	eq(shell.search("   ").size(), 0, "blank search")


func test_runner_lifecycle() -> void:
	var proc := OS.get_cache_dir() + "/gfg-shell-test-life-%d" % OS.get_process_id()
	DirAccess.make_dir_recursive_absolute(proc)
	var r := GameRunner.new()
	r._proc_root = proc
	var seen := []
	r.state_changed.connect(func(s, _g): seen.append(s))
	r.resolve_game = func(appid): return {"appid": appid, "name": "outside"}
	OS.set_environment("GFG_SHELL_STEAM_CMD", "/bin/true")
	var g := {"appid": 4100010, "name": "Neon Drift", "launch_id": "4100010"}
	check(r.launch(g), "launch accepted")
	check(not r.launch(g), "second launch while launching refused")
	eq(r._last_launch_cmd, PackedStringArray(["/bin/true", "steam://rungameid/4100010"]), "launch goes through steam URI")
	r.poll()
	eq(r.state, "launching", "still launching without process")
	DirAccess.make_dir_recursive_absolute(proc + "/4242")
	var f := FileAccess.open(proc + "/4242/cmdline", FileAccess.WRITE)
	f.store_buffer(_cmd(["reaper", "SteamLaunch", "AppId=4100010", "--", "game"]))
	f.close()
	r.poll()
	eq(r.state, "running", "running once reaper appears")
	r.poll()
	OS.execute("rm", ["-rf", proc + "/4242"])
	r.poll()
	eq(seen, ["launching", "running", "exited", "idle"], "full lifecycle")
	# a game started outside the shell (e.g. from Steam) is tracked too
	DirAccess.make_dir_recursive_absolute(proc + "/77")
	f = FileAccess.open(proc + "/77/cmdline", FileAccess.WRITE)
	f.store_buffer(_cmd(["reaper", "SteamLaunch", "AppId=555", "--", "x"]))
	f.close()
	r.poll()
	eq([r.state, r.running_appid, r.game.get("name")], ["running", 555, "outside"], "outside launch tracked")
	OS.execute("rm", ["-rf", proc])
	r.poll()
	eq(r.state, "idle", "outside game exit")
	r.free()
	OS.set_environment("GFG_SHELL_STEAM_CMD", "")
	test_shortcut_detection()


func _proc(root: String, pid: String, cmd: Array, env: Array = []) -> void:
	DirAccess.make_dir_recursive_absolute(root + "/" + pid)
	var f := FileAccess.open(root + "/" + pid + "/cmdline", FileAccess.WRITE)
	f.store_buffer(_cmd(cmd))
	f.close()
	if not env.is_empty():
		f = FileAccess.open(root + "/" + pid + "/environ", FileAccess.WRITE)
		f.store_buffer(_cmd(env))
		f.close()


## Non-Steam shortcuts: the marker may carry the 64-bit game id, a signed 32-bit id, or
## only SteamGameId in the environment (no reaper at all).
func test_shortcut_detection() -> void:
	OS.set_environment("GFG_SHELL_STEAM_CMD", "/bin/true")
	var g := {"appid": 2474520780, "name": "Arcade", "launch_id": "10627985823405965312", "kind": "shortcut"}
	eq(GameRunner.game_ids(g), ["2474520780", "-1820446516", "10627985823405965312"], "shortcut ids")
	for variant in [["reaper", "SteamLaunch", "AppId=10627985823405965312", "--", "x"],
			["reaper", "SteamLaunch", "AppId=-1820446516", "--", "x"], ["wine", "game.exe"]]:
		var proc := OS.get_cache_dir() + "/gfg-shell-test-sc-%d" % OS.get_process_id()
		DirAccess.make_dir_recursive_absolute(proc)
		_proc(proc, "10", ["bash"])
		var r := GameRunner.new()
		r._proc_root = proc
		check(r.launch(g), "shortcut launch accepted")
		var env := ["HOME=/home/deck", "SteamGameId=10627985823405965312"] if variant[0] == "wine" else []
		_proc(proc, "4000", variant, env)
		r.poll()
		eq(r.state, "running", "shortcut detected: %s" % variant[2] if variant.size() > 2 else "shortcut detected by environ")
		OS.execute("rm", ["-rf", proc + "/4000"])
		r.poll()
		eq(r.state, "idle", "shortcut exit detected (%s)" % variant[0])
		r.free()
		OS.execute("rm", ["-rf", proc])
	OS.set_environment("GFG_SHELL_STEAM_CMD", "")
	eq(GameRunner.env_value(_cmd(["A=1", "SteamGameId=42", "B=2"]), "SteamGameId"), "42", "env value")
	# the shell's own Steam marker is never taken for a game
	var proc2 := OS.get_cache_dir() + "/gfg-shell-test-self-%d" % OS.get_process_id()
	_proc(proc2, "77", ["reaper", "SteamLaunch", "AppId=3000000001", "--", "gfg-shell.sh"])
	var r2 := GameRunner.new()
	r2._proc_root = proc2
	r2.self_ids = ["3000000001"]
	r2.poll()
	eq(r2.state, "idle", "own SteamLaunch marker ignored")
	r2.self_ids = []
	r2.poll()
	eq(r2.state, "running", "an outside game is still tracked")
	r2.free()
	OS.execute("rm", ["-rf", proc2])
	eq(GameRunner.parse_steamlaunch_value(_cmd(["reaper", "SteamLaunch", "AppId=10627985823405965312", "--"])), "10627985823405965312", "64-bit AppId kept as text")


## An owned game that is not on the device goes to Steam's install dialog, not to a
## 3-minute wait for a process.
func test_install_launch() -> void:
	OS.set_environment("GFG_SHELL_STEAM_CMD", "/bin/true")
	var r := GameRunner.new()
	r._proc_root = OS.get_cache_dir() + "/gfg-shell-test-none"
	var failed := []
	r.launch_failed.connect(func(_g, reason): failed.append(reason))
	check(r.launch({"kind": "steam", "appid": 4100110, "name": "Frost Signal", "installed": false, "launch_id": "4100110"}), "install request handled")
	eq(r._last_launch_cmd, PackedStringArray(["/bin/true", "steam://install/4100110"]), "uninstalled game opens steam://install")
	eq([r.state, failed], ["idle", ["not-installed"]], "no launch wait for an uninstalled game")
	r.free()
	OS.set_environment("GFG_SHELL_STEAM_CMD", "")


func test_input_map() -> void:
	var shell: Node = root.get_node_or_null("Shell")
	if shell != null and not shell.is_node_ready():
		shell._setup_input()   # -s runs before autoloads are ready
	var has_a := InputMap.action_get_events("ui_accept").any(func(e): return e is InputEventJoypadButton and e.button_index == JOY_BUTTON_A)
	var has_b := InputMap.action_get_events("ui_cancel").any(func(e): return e is InputEventJoypadButton and e.button_index == JOY_BUTTON_B)
	check(shell != null and has_a, "A selects (ui_accept)")
	check(shell != null and has_b, "B goes back (ui_cancel)")
