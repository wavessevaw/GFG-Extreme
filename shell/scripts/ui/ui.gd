## GFG Shell look (dark + red, from the GFG/SteamOS concept mockups) and small widget factories.
## Everything is built in code so screens stay diff-able and testable headless.
class_name UI
extends RefCounted

const BG := Color("0a0a0d")
const BG2 := Color("111116")
const CARD := Color("17171d")
const CARD_HI := Color("1f1f27")
const LINE := Color("2a2a33")
const RED := Color("e3262f")
const RED_DIM := Color("7a1418")
const TEXT := Color("f2f2f5")
const TEXT_DIM := Color("9a9aa6")
const GREEN := Color("3ccf6e")
const AMBER := Color("f0a830")

const RADIUS := 10
const FOCUS_W := 3

static var _theme: Theme


static func theme() -> Theme:
	if _theme != null:
		return _theme
	var t := Theme.new()
	t.default_font_size = 18
	var sys := SystemFont.new()
	sys.font_names = PackedStringArray(["Noto Sans", "DejaVu Sans", "Cantarell", "sans-serif"])
	t.default_font = sys
	for cls in ["Label", "Button", "LineEdit", "CheckButton"]:
		t.set_color("font_color", cls, TEXT)
	t.set_color("font_hover_color", "Button", TEXT)
	t.set_color("font_focus_color", "Button", TEXT)
	t.set_color("font_pressed_color", "Button", TEXT)
	t.set_stylebox("normal", "Button", box(CARD))
	t.set_stylebox("hover", "Button", box(CARD_HI))
	t.set_stylebox("pressed", "Button", box(RED_DIM))
	t.set_stylebox("disabled", "Button", box(BG2))
	t.set_stylebox("focus", "Button", focus_box())
	t.set_stylebox("normal", "LineEdit", box(CARD, LINE))
	t.set_stylebox("focus", "LineEdit", focus_box())
	t.set_stylebox("panel", "PanelContainer", box(CARD))
	t.set_stylebox("panel", "Panel", box(CARD))
	var sb_scroll := StyleBoxFlat.new()
	sb_scroll.bg_color = Color(1, 1, 1, 0.06)
	t.set_stylebox("scroll", "VScrollBar", sb_scroll)
	t.set_stylebox("grabber", "VScrollBar", box(LINE))
	_theme = t
	return t


static func box(bg: Color, border: Color = Color.TRANSPARENT, radius: int = RADIUS, pad: int = 12) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.set_corner_radius_all(radius)
	s.content_margin_left = pad
	s.content_margin_right = pad
	s.content_margin_top = pad * 0.66
	s.content_margin_bottom = pad * 0.66
	if border.a > 0:
		s.set_border_width_all(1)
		s.border_color = border
	return s


static func focus_box() -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.draw_center = false
	s.set_corner_radius_all(RADIUS + 2)
	s.set_border_width_all(FOCUS_W)
	s.border_color = RED
	s.expand_margin_left = 3
	s.expand_margin_right = 3
	s.expand_margin_top = 3
	s.expand_margin_bottom = 3
	return s


static func label(text: String, size: int = 18, color: Color = TEXT, bold: bool = false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	if bold:
		var f := SystemFont.new()
		f.font_names = PackedStringArray(["Noto Sans", "DejaVu Sans", "sans-serif"])
		f.font_weight = 700
		l.add_theme_font_override("font", f)
	return l


static func button(text: String, primary: bool = false, min_w: int = 0, h: int = 48) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_ALL
	b.custom_minimum_size = Vector2(min_w, h)
	if primary:
		b.add_theme_stylebox_override("normal", box(RED))
		b.add_theme_stylebox_override("hover", box(RED.lightened(0.1)))
		b.add_theme_stylebox_override("pressed", box(RED.darkened(0.2)))
		var f := focus_box()
		f.border_color = TEXT
		b.add_theme_stylebox_override("focus", f)
	return b


## Toggle row button: "Name ........ [ON]". Returns the Button; update via set_toggle().
static func toggle(text: String, on: Variant) -> Button:
	var b := button("", false, 0, 56)
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.set_meta("title", text)
	set_toggle(b, on)
	return b


static func set_toggle(b: Button, on: Variant) -> void:
	var state := "—" if on == null else ("ВКЛ" if on else "ВЫКЛ")
	b.text = "%s    %s" % [b.get_meta("title"), state]
	b.add_theme_color_override("font_color", TEXT if on != false else TEXT_DIM)


static func vbox(sep: int = 12) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", sep)
	return v


static func hbox(sep: int = 12) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", sep)
	return h


static func panel(bg: Color = CARD, pad: int = 16) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", box(bg, Color.TRANSPARENT, RADIUS, pad))
	return p


static func margin(c: Control, l: int, t: int, r: int, b: int) -> MarginContainer:
	var m := MarginContainer.new()
	m.add_theme_constant_override("margin_left", l)
	m.add_theme_constant_override("margin_top", t)
	m.add_theme_constant_override("margin_right", r)
	m.add_theme_constant_override("margin_bottom", b)
	m.add_child(c)
	return m


static func spacer(h: bool = true) -> Control:
	var c := Control.new()
	if h:
		c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	else:
		c.size_flags_vertical = Control.SIZE_EXPAND_FILL
	return c


static func fmt_playtime(minutes: int) -> String:
	if minutes <= 0:
		return "не запускалась"
	if minutes < 60:
		return "%d мин" % minutes
	return "%.1f ч" % (minutes / 60.0)


static func fmt_last_played(ts: int) -> String:
	if ts <= 0:
		return "—"
	var days := int((Time.get_unix_time_from_system() - ts) / 86400)
	if days <= 0:
		return "сегодня"
	if days == 1:
		return "вчера"
	if days < 30:
		return "%d дн. назад" % days
	return Time.get_date_string_from_unix_time(ts)


static func fmt_size(bytes: int) -> String:
	if bytes <= 0:
		return "—"
	var gb := bytes / 1073741824.0
	return ("%.1f ГБ" % gb) if gb >= 1.0 else ("%d МБ" % int(bytes / 1048576.0))


static func mode_name(mode: String) -> String:
	return {"budget": "Батарея", "balanced": "Баланс", "quality": "Качество",
		"autopilot": "Autopilot", "extreme": "Extreme"}.get(mode, mode if mode != "" else "—")
