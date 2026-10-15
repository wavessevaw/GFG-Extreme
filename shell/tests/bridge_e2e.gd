## Godot BridgeClient <-> real Python ShellBridge (tools/fake_bridge.py) end to end.
## GFG_SHELL_BRIDGE_FILE=<discovery json> godot --headless --path shell -s res://tests/bridge_e2e.gd
extends SceneTree

var client: BridgeClient
var t := 0.0
var step := 0
var results := {}


func _initialize() -> void:
	client = BridgeClient.new()
	root.add_child(client)


func _process(delta: float) -> bool:
	t += delta
	if t > 20.0:
		printerr("FAIL: timeout at step %d (%s)" % [step, client.last_error])
		return _finish(1)
	match step:
		0:
			if client.connected and not client.status.is_empty():
				results["status_mode"] = client.status.get("mode")
				step = 1
				client.set_mode("quality", func(ok, _r): results["set_mode"] = ok; step = 2)
		2:
			step = 3
			client.set_continuous_boost(true, func(ok, _r): results["boost"] = ok; step = 4)
		4:
			step = 5
			client.call_method("set_mode", {"mode": "extreme"}, func(ok, r): results["extreme"] = [ok, r.get("error")]; step = 6)
		6:
			step = 7
			client.call_method("status", {}, func(ok, r): results["after"] = [ok, r.get("mode"), r.get("continuous_boost")]; step = 8)
		8:
			var want := {"status_mode": "autopilot", "set_mode": true, "boost": true,
				"extreme": [false, "mode-not-allowed"], "after": [true, "quality", true]}
			var bad := 0
			for k in want.keys():
				if results.get(k) != want[k]:
					printerr("FAIL: %s got %s want %s" % [k, str(results.get(k)), str(want[k])])
					bad += 1
			print("bridge e2e: %d checks, %d failures" % [want.size(), bad])
			return _finish(bad)
	return false


func _finish(code: int) -> bool:
	quit(code)
	return true
