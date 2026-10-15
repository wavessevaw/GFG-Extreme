## On-screen keyboard (mockup 08): QWERTY / ЙЦУКЕН, ⌫, Найти, ⇧, ?123, space, EN/RU,
## hide. Steam's keyboard is not reachable from a non-Steam client in every mode, so the
## shell carries its own. Emits text_changed on every key and submitted on Найти.
class_name Osk
extends VBoxContainer

signal text_changed(text: String)
signal submitted(text: String)
signal hide_requested

const LAYOUTS := {
	"en": [["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"], ["a", "s", "d", "f", "g", "h", "j", "k", "l"], ["z", "x", "c", "v", "b", "n", "m", ",", "."]],
	"ru": [["й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х"], ["ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э"], ["я", "ч", "с", "м", "и", "т", "ь", "б", "ю", "."]],
	"num": [["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"], ["-", "_", ":", ";", "(", ")", "!", "?", "'"], ["&", "+", "#", "/", "*", "@", ",", "."]],
}
const KEY_H := 60

var text := ""
var layout := "ru"
var _base := "ru"
var _shift := false
var _rows: VBoxContainer


func _ready() -> void:
	add_theme_constant_override("separation", 8)
	_rows = UI.vbox(8)
	add_child(_rows)
	_build()


func _key(label_text: String, w: int, cb: Callable, primary := false, icon := "") -> Button:
	var b := UI.button(label_text if icon == "" else "", primary, w, KEY_H, icon)
	if icon == "" and not primary:
		b.add_theme_font_size_override("font_size", 22)
		b.add_theme_font_override("font", UI.font("medium"))
	b.pressed.connect(cb)
	return b


func _build() -> void:
	var keep := _focused_index()
	for c in _rows.get_children():
		_rows.remove_child(c)
		c.queue_free()
	var rows: Array = LAYOUTS[layout]
	var kw := 86 if rows[0].size() >= 11 else 94
	for r in 3:
		var h := UI.hbox(8)
		h.alignment = BoxContainer.ALIGNMENT_CENTER
		if r == 2:
			h.add_child(_key("", 104, func(): _shift = not _shift; _build(), false, "shift"))
		for ch in rows[r]:
			var shown: String = ch.to_upper() if (_shift or layout != "num") else ch
			h.add_child(_key(shown, kw, _type.bind(ch.to_upper() if _shift else ch)))
		if r == 0:
			h.add_child(_key("", 116, _backspace, false, "backspace"))
		elif r == 1:
			h.add_child(_key("Найти", 150, func(): submitted.emit(text), true))
		_rows.add_child(h)
	var last := UI.hbox(8)
	last.alignment = BoxContainer.ALIGNMENT_CENTER
	last.add_child(_key("?123" if layout != "num" else "АБВ", 120, func():
		layout = _base if layout == "num" else "num"
		_build()))
	last.add_child(_key("", 560, _type.bind(" ")))
	last.add_child(_key("EN / RU", 140, func():
		_base = "en" if _base == "ru" else "ru"
		layout = _base
		_build()))
	last.add_child(_key("", 120, func(): hide_requested.emit(), false, "keyboard"))
	_rows.add_child(last)
	if keep >= 0:
		_focus_index.call_deferred(keep)


func _all_keys() -> Array:
	var out := []
	for h in _rows.get_children():
		for b in h.get_children():
			out.append(b)
	return out


func _focused_index() -> int:
	if _rows == null:
		return -1
	var f := get_viewport().gui_get_focus_owner() if is_inside_tree() else null
	return _all_keys().find(f)


func _focus_index(i: int) -> void:
	var keys := _all_keys()
	if keys.is_empty():
		return
	keys[clampi(i, 0, keys.size() - 1)].grab_focus()


func _type(ch: String) -> void:
	text += ch
	if _shift:
		_shift = false
		_build()
	text_changed.emit(text)


func _backspace() -> void:
	text = text.substr(0, max(0, text.length() - 1))
	text_changed.emit(text)


func clear() -> void:
	text = ""
	text_changed.emit(text)


func focus_first() -> void:
	_focus_index(0)
