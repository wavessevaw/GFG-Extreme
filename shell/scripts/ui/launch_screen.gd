## Экран запуска: from Play until Steam's process tree for the game appears, then while
## it runs (the game window covers the shell) until it exits. B while waiting stops
## *waiting* only; the shell never terminates a game or Steam.
class_name LaunchScreen
extends Control

var app: Node
var phase := ""        # launching | running | failed
var game: Dictionary = {}
var _back: Control
var _logo: TextureRect
var _title: Label
var _status: Label
var _hint: Label
var _spinner: Control
var _t := 0.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	z_index = 60
	visible = false
	var bg := ColorRect.new()
	bg.color = UI.BG
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	_back = UI.hero_backdrop()
	add_child(_back)
	var v := UI.vbox(16)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 80
	v.offset_right = -80
	add_child(v)
	_logo = TextureRect.new()
	_logo.custom_minimum_size = Vector2(520, 150)
	_logo.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT
	v.add_child(_logo)
	_title = UI.label("", 52, UI.TEXT, "bold")
	v.add_child(_title)
	var sh := UI.hbox(14)
	_spinner = Control.new()
	_spinner.custom_minimum_size = Vector2(30, 30)
	_spinner.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_spinner.draw.connect(func():
		var c := _spinner.size / 2
		_spinner.draw_arc(c, 12, 0, TAU, 40, Color(1, 1, 1, 0.15), 4, true)
		if phase == "launching":
			_spinner.draw_arc(c, 12, _t * 5.0, _t * 5.0 + 1.8, 24, UI.RED, 4, true)
		elif phase == "running":
			_spinner.draw_circle(c, 7, UI.GREEN)
		else:
			_spinner.draw_circle(c, 7, UI.RED))
	sh.add_child(_spinner)
	_status = UI.label("", 22, UI.TEXT, "semibold")
	sh.add_child(_status)
	v.add_child(sh)
	_hint = UI.label("", 16, UI.TEXT_DIM, "regular")
	v.add_child(_hint)


func begin(g: Dictionary) -> void:
	game = g
	phase = "launching"
	visible = true
	_title.text = str(g.get("name", ""))
	_title.visible = true
	_logo.texture = null
	_logo.visible = false
	_status.text = "Запуск через Steam…"
	_hint.text = "Steam может сначала синхронизировать сохранения или обновить игру.      Ⓑ  Перестать ждать"
	var art: Dictionary = g.get("art", {})
	var tex: TextureRect = _back.get_node("Art")
	tex.texture = null
	Shell.load_art(art.get("hero", art.get("header", "")), func(t): tex.texture = t)
	if art.has("logo"):
		Shell.load_art(art.logo, func(t): _logo.texture = t; _logo.visible = true; _title.visible = false)


func running(g: Dictionary) -> void:
	if not visible:
		begin(g)
	phase = "running"
	_status.text = "Игра запущена"
	_hint.text = "После выхода из игры вы вернётесь в GFG Shell."


func failed(g: Dictionary, reason: String) -> void:
	if not visible:
		begin(g)
	phase = "failed"
	_status.text = "Игра не запустилась" if reason != "timeout" else "Steam не запустил игру за 3 минуты"
	_hint.text = "Причина: %s. Проверьте окно Steam.      Ⓑ  Назад" % reason


func on_back() -> void:
	if phase == "launching":
		Shell.runner.cancel_wait()
		close()
	elif phase == "failed":
		close()


func close() -> void:
	visible = false
	phase = ""


func _process(delta: float) -> void:
	if visible:
		_t += delta
		_spinner.queue_redraw()
