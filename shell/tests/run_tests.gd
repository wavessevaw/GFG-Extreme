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
	if fixture != "":
		test_library()
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


func test_shortcut_id() -> void:
	eq(SteamLibrary.shortcut_game_id(-1820446516), "10627985823405965312", "shortcut id with sign bit")
	eq(SteamLibrary.shortcut_game_id(2081234567), "8938834400603275264", "shortcut id positive")


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
	eq(games.size(), 10, "8 Steam games + 2 shortcuts (tool, broken manifest, shell hidden)")
	check(not by.has("Proton Experimental"), "Proton hidden")
	check(not by.has("GFG Shell"), "shell hides itself")
	check(lib.errors.has("bad-manifest:appmanifest_9999.acf"), "truncated manifest reported")
	eq(games.filter(func(g): return g.installed).size(), 9, "installed count (StateFlags bit 4)")
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
	eq(SteamLibrary.new().load_library(fixture + "/nope"), [], "missing root yields empty library")


func test_state_queries() -> void:
	var shell: Node = root.get_node_or_null("Shell")
	check(shell != null, "Shell autoload present")
	if shell == null:
		return
	shell.games = shell.library.load_library(fixture + "/Steam")
	shell.favorites = {}
	var recent: Array = shell.recent_games(3)
	eq(recent.map(func(g): return g.name), ["Neon Drift", "Пепел Севера", "Retro Arcade Hub"], "recent order")
	eq(shell.favorite_games().size(), 2, "favorites from Steam")
	var nd: Dictionary = shell.games.filter(func(g): return g.name == "Neon Drift")[0]
	shell.favorites[nd.id] = true
	eq(shell.favorite_games().size(), 3, "GFG favorite added")
	var pep: Dictionary = shell.games.filter(func(g): return g.name == "Пепел Севера")[0]
	shell.favorites[pep.id] = false
	eq(shell.favorite_games().size(), 2, "GFG override removes Steam favorite")
	eq(shell.search("пеп").size(), 1, "cyrillic search")
	eq(shell.search("o")[0].name.to_lower().begins_with("o"), true, "prefix match first")
	eq(shell.filtered_games("nonsteam", "name").size(), 2, "non-Steam filter")
	eq(shell.filtered_games("installed", "name").size(), 9, "installed filter")
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
