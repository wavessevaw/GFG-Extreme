## GFG Bridge client: talks to the GFG Extreme plugin over loopback TCP (see
## py_modules/gfg_plugin/shell_bridge.py). Discovery file holds port + token.
## The shell never controls TDP/GPU itself: every power-related action is a
## Governor setting forwarded through this link.
class_name BridgeClient
extends Node

signal connection_changed(connected: bool)
signal status_updated(status: Dictionary)

const POLL_S := 1.0
const RETRY_S := 5.0
const REQUEST_TIMEOUT_S := 6.0

var connected := false
var status: Dictionary = {}
var last_error := ""
var _peer: StreamPeerTCP
var _token := ""
var _authed := false
var _buf := PackedByteArray()
var _next_id := 1
var _pending := {}       # id -> {cb: Callable, at: float}
var _accum := 0.0
var _retry_accum := RETRY_S
var active := true       # false while a game runs and the panel is closed: slower polling


static func discovery_path() -> String:
	var env := OS.get_environment("GFG_SHELL_BRIDGE_FILE")
	if env != "":
		return env
	return OS.get_environment("HOME") + "/.local/state/gfg-extreme/shell-bridge.json"


func _process(delta: float) -> void:
	if _peer == null:
		_retry_accum += delta
		if _retry_accum >= RETRY_S:
			_retry_accum = 0.0
			_try_connect()
		return
	_peer.poll()
	var st := _peer.get_status()
	if st == StreamPeerTCP.STATUS_CONNECTING:
		return
	if st != StreamPeerTCP.STATUS_CONNECTED:
		_drop("socket-closed")
		return
	if not connected:
		connected = true
		Log.info("bridge", "connected")
		connection_changed.emit(true)
		call_method("hello", {}, func(ok, r): if ok: Log.info("bridge", "api %s" % str(r.get("api"))))
	_read()
	_expire()
	_accum += delta
	if _accum >= (POLL_S if active else POLL_S * 4.0):
		_accum = 0.0
		call_method("status", {}, _on_status)


func _try_connect() -> void:
	var path := discovery_path()
	if not FileAccess.file_exists(path):
		last_error = "plugin-not-running"
		return
	var info: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (info is Dictionary) or not info.has("port") or not info.has("token"):
		last_error = "bad-discovery-file"
		return
	_token = str(info.token)
	_peer = StreamPeerTCP.new()
	if _peer.connect_to_host("127.0.0.1", int(info.port)) != OK:
		_peer = null
		last_error = "connect-failed"


func _drop(reason: String) -> void:
	if connected:
		Log.warn("bridge", "disconnected: " + reason)
	last_error = reason
	_peer = null
	_authed = false
	_buf.clear()
	for id in _pending.keys():
		_pending[id].cb.call(false, {"error": reason})
	_pending.clear()
	if connected:
		connected = false
		connection_changed.emit(false)


## cb(ok: bool, result_or_error: Dictionary)
func call_method(method: String, params: Dictionary, cb: Callable = Callable()) -> void:
	if _peer == null or not connected:
		if cb.is_valid():
			cb.call(false, {"error": "not-connected"})
		return
	var id := _next_id
	_next_id += 1
	var req := {"id": id, "method": method, "params": params}
	if not _authed:
		req["token"] = _token
		_authed = true
	_pending[id] = {"cb": cb if cb.is_valid() else func(_a, _b): pass, "at": Time.get_ticks_msec() / 1000.0}
	_peer.put_data((JSON.stringify(req) + "\n").to_utf8_buffer())


func _read() -> void:
	var avail := _peer.get_available_bytes()
	if avail <= 0:
		return
	var got := _peer.get_partial_data(avail)
	if got[0] != OK:
		return
	_buf.append_array(got[1])
	while true:
		var nl := _buf.find(10)
		if nl < 0:
			break
		var line := _buf.slice(0, nl).get_string_from_utf8()
		_buf = _buf.slice(nl + 1)
		var msg: Variant = JSON.parse_string(line)
		if not (msg is Dictionary):
			continue
		var id := int(msg.get("id", -1)) if msg.get("id") != null else -1
		if msg.get("error") == "unauthorized":
			Log.error("bridge", "token rejected")
			_drop("unauthorized")
			return
		if _pending.has(id):
			var p: Dictionary = _pending[id]
			_pending.erase(id)
			if msg.get("ok") == true:
				p.cb.call(true, msg.get("result", {}) if msg.get("result") is Dictionary else {})
			else:
				p.cb.call(false, {"error": str(msg.get("error", "failed"))})


func _expire() -> void:
	var now := Time.get_ticks_msec() / 1000.0
	for id in _pending.keys():
		if now - float(_pending[id].at) > REQUEST_TIMEOUT_S:
			var p: Dictionary = _pending[id]
			_pending.erase(id)
			p.cb.call(false, {"error": "timeout"})


func _on_status(ok: bool, r: Dictionary) -> void:
	if ok:
		status = r
		status_updated.emit(r)


# Convenience wrappers: each is one Governor setting, nothing more.
func set_mode(mode: String, cb: Callable = Callable()) -> void:
	Log.info("bridge", "set_mode " + mode)
	call_method("set_mode", {"mode": mode}, cb)


func set_frame_fusion(enabled: bool, cb: Callable = Callable()) -> void:
	Log.info("bridge", "set_frame_fusion %s" % enabled)
	call_method("set_frame_fusion", {"enabled": enabled}, cb)


func set_feature(feature: String, enabled: bool, cb: Callable = Callable()) -> void:
	Log.info("bridge", "set_feature %s %s" % [feature, enabled])
	call_method("set_feature", {"feature": feature, "enabled": enabled}, cb)


func set_enabled(enabled: bool, cb: Callable = Callable()) -> void:
	Log.info("bridge", "set_enabled %s" % enabled)
	call_method("set_enabled", {"enabled": enabled}, cb)


func set_preference(preference: String, cb: Callable = Callable()) -> void:
	Log.info("bridge", "set_preference " + preference)
	call_method("set_preference", {"preference": preference}, cb)


func set_hud(enabled: bool, cb: Callable = Callable()) -> void:
	Log.info("bridge", "set_hud %s" % enabled)
	call_method("set_hud", {"enabled": enabled}, cb)


func set_boost(enabled: bool, cb: Callable = Callable()) -> void:
	Log.info("bridge", "set_feature boost %s" % enabled)
	call_method("set_feature", {"feature": "boost", "enabled": enabled}, cb)


func set_continuous_boost(enabled: bool, cb: Callable = Callable()) -> void:
	Log.info("bridge", "set_feature continuous_boost %s" % enabled)
	call_method("set_feature", {"feature": "continuous_boost", "enabled": enabled}, cb)
