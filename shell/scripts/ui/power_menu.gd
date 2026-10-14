## Питание: suspend / reboot / power off through logind, exit to Steam. Confirms the
## destructive choices; never stops Steam itself.
class_name PowerMenu
extends Control

var app: Node
var _box: VBoxContainer
var _prev_focus: Control
var _confirm := ""


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	visible = false
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.65)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var p := UI.panel(UI.BG2, 28)
	p.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	p.custom_minimum_size = Vector2(440, 0)
	p.position = Vector2(-220, -230)
	add_child(p)
	_box = UI.vbox(10)
	p.add_child(_box)


func open() -> void:
	_prev_focus = get_viewport().gui_get_focus_owner()
	_confirm = ""
	_build()
	visible = true


func _build() -> void:
	for c in _box.get_children():
		c.queue_free()
	if _confirm == "":
		_box.add_child(UI.label("Питание", 26, UI.TEXT, true))
		for a in [["suspend", "Спящий режим"], ["reboot", "Перезагрузка"], ["poweroff", "Выключение"], ["exit", "Выйти из GFG Shell"], ["cancel", "Отмена"]]:
			var b := UI.button(a[1], a[0] == "suspend", 0, 54)
			b.pressed.connect(_choose.bind(a[0]))
			_box.add_child(b)
	else:
		var names := {"reboot": "Перезагрузить Steam Deck?", "poweroff": "Выключить Steam Deck?", "exit": "Выйти из GFG Shell в Steam?"}
		_box.add_child(UI.label(names[_confirm], 22, UI.TEXT, true))
		if _confirm != "exit":
			_box.add_child(UI.label("Несохранённый прогресс в играх может быть потерян.", 15, UI.TEXT_DIM))
		var yes := UI.button("Да", true, 0, 54)
		yes.pressed.connect(_do.bind(_confirm))
		_box.add_child(yes)
		var no := UI.button("Нет", false, 0, 54)
		no.pressed.connect(func(): _confirm = ""; _build())
		_box.add_child(no)
	_focus_first.call_deferred()


func _focus_first() -> void:
	for c in _box.get_children():
		if c is Button:
			c.grab_focus()
			return


func _choose(a: String) -> void:
	match a:
		"cancel": close()
		"suspend": _do("suspend")
		_:
			_confirm = a
			_build()


func _do(a: String) -> void:
	close()
	if a == "exit":
		app.quit_shell()
	else:
		var code := SystemInfo.power(a)
		if code != 0:
			app.toast("Команда питания не выполнена (код %d)" % code)


func close() -> void:
	visible = false
	if _prev_focus != null and is_instance_valid(_prev_focus) and _prev_focus.is_visible_in_tree():
		_prev_focus.grab_focus()
