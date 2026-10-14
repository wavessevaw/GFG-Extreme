## Controller on-screen keyboard (RU/EN). Steam's keyboard is not available to a non-Steam
## client in every mode, so the shell carries its own. Emits text_changed on every key.
class_name Osk
extends VBoxContainer

signal text_changed(text: String)
signal submitted(text: String)

const LAYOUTS := {
	"ru": ["1234567890", "йцукенгшщзх", "фывапролджэ", "ячсмитьбю"],
	"en": ["1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"],
}

var text := ""
var layout := "ru"
var _rows: VBoxContainer


func _ready() -> void:
	add_theme_constant_override("separation", 8)
	_rows = UI.vbox(8)
	add_child(_rows)
	_build()


func _build() -> void:
	for c in _rows.get_children():
		c.queue_free()
	for line in LAYOUTS[layout]:
		var h := UI.hbox(6)
		h.alignment = BoxContainer.ALIGNMENT_CENTER
		for ch in line:
			var b := UI.button(ch.to_upper(), false, 50, 50)
			b.pressed.connect(_type.bind(ch))
			h.add_child(b)
		_rows.add_child(h)
	var last := UI.hbox(6)
	last.alignment = BoxContainer.ALIGNMENT_CENTER
	var lay := UI.button("RU/EN", false, 90, 50)
	lay.pressed.connect(func(): layout = "en" if layout == "ru" else "ru"; _build(); _rows.get_child(1).get_child(0).call_deferred("grab_focus"))
	last.add_child(lay)
	var sp := UI.button("Пробел", false, 240, 50)
	sp.pressed.connect(_type.bind(" "))
	last.add_child(sp)
	var bs := UI.button("⌫", false, 80, 50)
	bs.pressed.connect(func(): text = text.substr(0, max(0, text.length() - 1)); text_changed.emit(text))
	last.add_child(bs)
	var clr := UI.button("Очистить", false, 120, 50)
	clr.pressed.connect(func(): text = ""; text_changed.emit(text))
	last.add_child(clr)
	var ok := UI.button("Готово", true, 120, 50)
	ok.pressed.connect(func(): submitted.emit(text))
	last.add_child(ok)
	_rows.add_child(last)


func _type(ch: String) -> void:
	text += ch
	text_changed.emit(text)


func focus_first() -> void:
	(_rows.get_child(1).get_child(0) as Control).grab_focus()
