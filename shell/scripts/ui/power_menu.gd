## Питание: Сон / Перезагрузка / Выключение / Выйти из GFG Shell. Destructive choices
## ask once more. Suspend goes through logind like the stock menu; Steam is never stopped.
class_name PowerMenu
extends Overlay

var _box: VBoxContainer
var _confirm := ""


func _ready() -> void:
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.6)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var p := UI.panel(Color("111116"), 22, 16)
	p.custom_minimum_size = Vector2(460, 0)
	p.set_anchors_preset(Control.PRESET_CENTER)
	p.grow_horizontal = Control.GROW_DIRECTION_BOTH
	p.grow_vertical = Control.GROW_DIRECTION_BOTH
	add_child(p)
	_box = UI.vbox(6)
	p.add_child(_box)


func _on_open() -> void:
	_confirm = ""
	_build()


func _build() -> void:
	for c in _box.get_children():
		_box.remove_child(c)
		c.queue_free()
	if _confirm == "":
		var t := UI.label("Питание", 26, UI.TEXT, "bold")
		_box.add_child(UI.margin(t, 8, 0, 0, 8))
		for a in [["sleep", "Сон", "suspend"], ["refresh", "Перезагрузка", "reboot"], ["power", "Выключение", "poweroff"],
				["close", "Выйти из GFG Shell", "exit"]]:
			var b := UI.row(a[0], a[1], "", null, 60)
			b.pressed.connect(_choose.bind(a[2]))
			_box.add_child(b)
	else:
		var names := {"reboot": "Перезагрузить Steam Deck?", "poweroff": "Выключить Steam Deck?", "exit": "Выйти из GFG Shell в Steam?"}
		_box.add_child(UI.margin(UI.label(names[_confirm], 22, UI.TEXT, "bold"), 8, 0, 0, 4))
		if _confirm != "exit":
			_box.add_child(UI.margin(UI.label("Несохранённый прогресс в играх может быть потерян.", 15, UI.TEXT_DIM, "regular"), 8, 0, 0, 8))
		var yes := UI.button("Да", true, 0, 56)
		yes.pressed.connect(_do.bind(_confirm))
		_box.add_child(yes)
		var no := UI.button("Отмена", false, 0, 56)
		no.pressed.connect(func(): _confirm = ""; _build(); _focus_first.call_deferred())
		_box.add_child(no)
	_focus_first.call_deferred()


func _choose(a: String) -> void:
	if a == "suspend":
		_do("suspend")
	else:
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
