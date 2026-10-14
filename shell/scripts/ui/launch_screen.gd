## Экран запуска: shown from the Play press until Steam's process tree for the game appears,
## then while it runs (the game window covers the shell), until it exits. B while waiting
## stops *waiting* only; the shell never terminates a game or Steam.
class_name LaunchScreen
extends Control

var app: Node
var phase := ""        # launching | running | failed
var game: Dictionary = {}
var _hero: TextureRect
var _title: Label
var _status: Label
var _hint: Label
var _spinner: Label
var _t := 0.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	visible = false
	var bg := ColorRect.new()
	bg.color = UI.BG
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	_hero = TextureRect.new()
	_hero.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_hero.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_hero.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_hero.modulate = Color(1, 1, 1, 0.35)
	add_child(_hero)
	var v := UI.vbox(14)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 80
	v.offset_right = -80
	add_child(v)
	v.add_child(UI.label("GFG", 22, UI.RED, true))
	_title = UI.label("", 40, UI.TEXT, true)
	v.add_child(_title)
	var sh := UI.hbox(12)
	_spinner = UI.label("◐", 26, UI.RED)
	sh.add_child(_spinner)
	_status = UI.label("", 20, UI.TEXT)
	sh.add_child(_status)
	v.add_child(sh)
	_hint = UI.label("", 16, UI.TEXT_DIM)
	v.add_child(_hint)


func begin(g: Dictionary) -> void:
	game = g
	phase = "launching"
	visible = true
	_title.text = str(g.get("name", ""))
	_status.text = "Запуск через Steam…"
	_hint.text = "Steam может сначала синхронизировать сохранения или обновить игру.   Ⓑ — перестать ждать"
	_hero.texture = null
	var art: Dictionary = g.get("art", {})
	Shell.load_art(art.get("hero", art.get("header", "")), func(t): _hero.texture = t)


func running(g: Dictionary) -> void:
	if not visible:
		begin(g)
	phase = "running"
	_status.text = "Игра запущена"
	_hint.text = "После выхода из игры вы вернётесь в GFG Shell."


func failed(g: Dictionary, reason: String) -> void:
	game = g
	phase = "failed"
	visible = true
	_status.text = "Игра не запустилась" if reason != "timeout" else "Steam не запустил игру за 3 минуты"
	_hint.text = "Причина: %s. Проверьте окно Steam.   Ⓑ — назад" % reason


func on_back() -> void:
	if phase == "launching":
		Shell.runner.cancel_wait()
		close()
	elif phase == "failed":
		close()
	# while running, B belongs to the game; the shell ignores it


func close() -> void:
	visible = false
	phase = ""


func _process(delta: float) -> void:
	if not visible:
		return
	_t += delta
	if phase == "launching":
		_spinner.text = ["◐", "◓", "◑", "◒"][int(_t * 6.0) % 4]
	else:
		_spinner.text = "●" if phase == "running" else "✕"
