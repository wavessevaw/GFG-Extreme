## Центр GFG Extreme: live telemetry (FPS, CPU, GPU, temp, TDP, battery) + Governor settings.
## Read-only for power: TDP/GPU clocks belong to the Governor.
extends Screen

var _tiles := {}
var _state: Label
var _controls: GfgControls


func _ready() -> void:
	title = "GFG Extreme"
	var v := UI.vbox(16)
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(UI.margin(v, 32, 12, 32, 12))
	get_child(0).set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var head := UI.hbox(12)
	head.add_child(UI.label("GFG EXTREME", 22, UI.RED, true))
	_state = UI.label("", 16, UI.TEXT_DIM)
	head.add_child(_state)
	v.add_child(head)
	var tiles := GridContainer.new()
	tiles.columns = 6
	tiles.add_theme_constant_override("h_separation", 12)
	v.add_child(tiles)
	for t in [["fps", "FPS"], ["real", "Реальные"], ["cpu", "CPU"], ["gpu", "GPU"], ["temp", "Темп."], ["tdp", "TDP"]]:
		var p := UI.panel(UI.CARD, 14)
		p.custom_minimum_size = Vector2(186, 96)
		var pv := UI.vbox(2)
		p.add_child(pv)
		pv.add_child(UI.label(t[1], 14, UI.TEXT_DIM))
		var val := UI.label("—", 30, UI.TEXT, true)
		pv.add_child(val)
		_tiles[t[0]] = val
		tiles.add_child(p)
	var cp := UI.panel(UI.CARD, 18)
	_controls = GfgControls.make(false, app.toast if app != null else Callable())
	cp.add_child(_controls)
	v.add_child(cp)
	Shell.bridge.status_updated.connect(func(_s): _refresh())
	Shell.bridge.connection_changed.connect(func(_c): _refresh())
	_refresh()


func _fmt(v: Variant, suffix: String, digits: int = 0) -> String:
	if v == null:
		return "—"
	return (("%." + str(digits) + "f") % float(v)) + suffix


func _refresh() -> void:
	var s := Shell.bridge.status if Shell.bridge.connected else {}
	_tiles.fps.text = _fmt(s.get("fps", {}).get("output"), "")
	_tiles.real.text = _fmt(s.get("fps", {}).get("real"), "")
	_tiles.cpu.text = _fmt(s.get("sensors", {}).get("cpu_pct"), "%")
	_tiles.gpu.text = _fmt(s.get("sensors", {}).get("gpu_busy_pct"), "%")
	_tiles.temp.text = _fmt(s.get("sensors", {}).get("temp_c"), "°")
	_tiles.tdp.text = _fmt(s.get("power", {}).get("tdp_w"), " Вт", 1)
	if Shell.bridge.connected:
		_state.text = "Governor: %s · %s" % [str(s.get("state", "—")), UI.mode_name(str(s.get("mode", "")))]
	else:
		_state.text = "не подключён — установите/запустите плагин GFG Extreme в Decky"
