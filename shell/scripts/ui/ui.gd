## GFG Shell look, matched to the GFG/SteamOS concept sheets: near-black base,
## full-bleed game art, red (#e1252b) for the active and focused element, white
## pill tabs, rounded dark cards with a hairline border, Inter typeface.
class_name UI
extends RefCounted

const BG := Color("0a0a0d")
const BG2 := Color("101014")
const CARD := Color("16161b")
const CARD_HI := Color("202027")
const LINE := Color(1, 1, 1, 0.07)
const RED := Color("e1252b")
const RED_DIM := Color("5a1013")
const TEXT := Color("f4f4f6")
const TEXT_DIM := Color("a2a2ad")
const MUTED := Color("6c6c77")
const GREEN := Color("3ccf6e")
const AMBER := Color("f0a830")

const RADIUS := 12

static var _theme: Theme
static var _fonts := {}


static func font(weight: String = "medium") -> Font:
	if _fonts.has(weight):
		return _fonts[weight]
	var file: String = {"regular": "Inter-Regular", "medium": "Inter-Medium", "semibold": "Inter-SemiBold",
		"bold": "Inter-Bold"}.get(weight, "Inter-Medium")
	var f: Font = load("res://assets/fonts/%s.ttf" % file)
	if f == null:
		var sys := SystemFont.new()
		sys.font_names = PackedStringArray(["Noto Sans", "DejaVu Sans", "sans-serif"])
		f = sys
	_fonts[weight] = f
	return f


static func theme() -> Theme:
	if _theme != null:
		return _theme
	var t := Theme.new()
	t.default_font = font("medium")
	t.default_font_size = 17
	for cls in ["Label", "Button", "LineEdit"]:
		t.set_color("font_color", cls, TEXT)
	for k in ["font_hover_color", "font_focus_color", "font_pressed_color", "font_hover_pressed_color"]:
		t.set_color(k, "Button", TEXT)
	t.set_color("font_disabled_color", "Button", MUTED)
	t.set_stylebox("normal", "Button", box(CARD, LINE))
	t.set_stylebox("hover", "Button", box(CARD_HI, LINE))
	t.set_stylebox("pressed", "Button", box(CARD_HI, LINE))
	t.set_stylebox("disabled", "Button", box(BG2, LINE))
	t.set_stylebox("focus", "Button", focus_box())
	t.set_stylebox("panel", "PanelContainer", box(CARD, LINE))
	t.set_stylebox("panel", "Panel", box(CARD, LINE))
	var thin := StyleBoxFlat.new()
	thin.bg_color = Color(1, 1, 1, 0.0)
	t.set_stylebox("scroll", "VScrollBar", thin)
	t.set_stylebox("scroll", "HScrollBar", thin)
	t.set_stylebox("grabber", "VScrollBar", box(Color(1, 1, 1, 0.15), Color.TRANSPARENT, 3, 0))
	t.set_stylebox("grabber", "HScrollBar", box(Color(1, 1, 1, 0.15), Color.TRANSPARENT, 3, 0))
	_theme = t
	return t


static func box(bg: Color, border: Color = Color.TRANSPARENT, radius: int = RADIUS, pad: int = 14) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.set_corner_radius_all(radius)
	s.content_margin_left = pad
	s.content_margin_right = pad
	s.content_margin_top = pad * 0.6
	s.content_margin_bottom = pad * 0.6
	if border.a > 0:
		s.set_border_width_all(1)
		s.border_color = border
	s.anti_aliasing = true
	return s


static func focus_box(color: Color = RED, radius: int = RADIUS + 2) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.draw_center = false
	s.set_corner_radius_all(radius)
	s.set_border_width_all(3)
	s.border_color = color
	s.expand_margin_left = 2
	s.expand_margin_right = 2
	s.expand_margin_top = 2
	s.expand_margin_bottom = 2
	return s


static func label(text: String, size: int = 17, color: Color = TEXT, weight: String = "medium") -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_font_override("font", font(weight))
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


## Button with an optional leading icon. primary = solid red (the mockups' "Играть").
static func button(text: String, primary: bool = false, min_w: int = 0, h: int = 52, icon: String = "") -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.custom_minimum_size = Vector2(min_w, h)
	b.add_theme_font_override("font", font("semibold"))
	b.add_theme_font_size_override("font_size", 18)
	if primary:
		b.add_theme_stylebox_override("normal", box(RED))
		b.add_theme_stylebox_override("hover", box(RED.lightened(0.08)))
		b.add_theme_stylebox_override("pressed", box(RED.darkened(0.15)))
		b.add_theme_stylebox_override("focus", focus_box(TEXT))
	if icon != "":
		var row := hbox(12)
		row.alignment = BoxContainer.ALIGNMENT_CENTER
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		row.add_child(GIcon.make(icon, 20))
		if text != "":
			var l := label(text, 18, TEXT, "semibold")
			row.add_child(l)
		b.add_child(row)
		if min_w == 0:
			b.custom_minimum_size.x = h if text == "" else 60 + text.length() * 11
	else:
		b.text = text
	return b


static func icon_button(icon: String, h: int = 52) -> Button:
	return button("", false, h, h, icon)


## Setting/list row: [icon] Title / subtitle ........ [right]. Focusable as one unit.
static func row(icon: String, title: String, subtitle: String = "", right: Control = null, h: int = 62) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.custom_minimum_size = Vector2(0, h if subtitle != "" else h - 8)
	b.add_theme_stylebox_override("normal", box(Color(0, 0, 0, 0), Color.TRANSPARENT, 10))
	b.add_theme_stylebox_override("hover", box(Color(1, 1, 1, 0.04), Color.TRANSPARENT, 10))
	b.add_theme_stylebox_override("pressed", box(Color(1, 1, 1, 0.06), Color.TRANSPARENT, 10))
	b.add_theme_stylebox_override("focus", focus_box(RED, 10))
	var m := MarginContainer.new()
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for side in ["left", "right"]:
		m.add_theme_constant_override("margin_" + side, 16)
	b.add_child(m)
	var h2 := hbox(16)
	h2.mouse_filter = Control.MOUSE_FILTER_IGNORE
	m.add_child(h2)
	if icon != "":
		h2.add_child(GIcon.make(icon, 24, TEXT))
	var v := VBoxContainer.new()
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_theme_constant_override("separation", 1)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var tl := label(title, 17, TEXT, "semibold")
	tl.name = "Title"
	v.add_child(tl)
	if subtitle != "":
		var sl := label(subtitle, 13, TEXT_DIM, "regular")
		sl.name = "Sub"
		sl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		v.add_child(sl)
	h2.add_child(v)
	if right != null:
		right.mouse_filter = Control.MOUSE_FILTER_IGNORE
		h2.add_child(right)
	return b


## "90 Гц  ›" value box used on the right of a row.
static func value_box(text: String) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", box(CARD_HI, LINE, 10, 16))
	p.custom_minimum_size = Vector2(130, 42)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var h := hbox(10)
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	var l := label(text, 16, TEXT, "semibold")
	l.name = "Value"
	h.add_child(l)
	h.add_child(GIcon.make("chevron", 16, TEXT_DIM))
	p.add_child(h)
	return p


## White round controller glyph (A / B / X / Y) for the hint bar.
static func glyph(letter: String) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(26, 26)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	c.draw.connect(func():
		c.draw_circle(c.size / 2, 12.5, TEXT)
		var f := font("bold")
		var ts := f.get_string_size(letter, HORIZONTAL_ALIGNMENT_LEFT, -1, 14)
		c.draw_string(f, Vector2((c.size.x - ts.x) / 2, c.size.y / 2 + 5), letter, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, BG))
	return c


## Small white pill with dark text ("МЕНЮ" style key cap).
static func keycap(text: String) -> PanelContainer:
	var p := PanelContainer.new()
	var sb := box(TEXT, Color.TRANSPARENT, 12, 10)
	sb.content_margin_top = 2
	sb.content_margin_bottom = 2
	p.add_theme_stylebox_override("panel", sb)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	p.add_child(label(text, 12, BG, "bold"))
	return p


static func chip(icon: String, text: String, sub: String = "") -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", box(Color(0.06, 0.06, 0.08, 0.85), LINE, 10, 16))
	p.custom_minimum_size = Vector2(0, 52)
	var h := hbox(12)
	h.add_child(GIcon.make(icon, 22, TEXT))
	var v := VBoxContainer.new()
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_theme_constant_override("separation", 0)
	v.add_child(label(text, 15, TEXT, "semibold"))
	if sub != "":
		v.add_child(label(sub, 12, TEXT_DIM, "regular"))
	h.add_child(v)
	p.add_child(h)
	return p


static func vbox(sep: int = 12) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", sep)
	return v


static func hbox(sep: int = 12) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", sep)
	return h


static func panel(bg: Color = CARD, pad: int = 18, radius: int = RADIUS) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", box(bg, LINE, radius, pad))
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
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if h:
		c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	else:
		c.size_flags_vertical = Control.SIZE_EXPAND_FILL
	return c


## Full-bleed art with the mockups' darkening: left-to-right and bottom-to-top gradients.
static func hero_backdrop() -> Control:
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var tex := TextureRect.new()
	tex.name = "Art"
	tex.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	tex.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(tex)
	for dir in [[Vector2(0, 0), Vector2(1, 0), 0.92, 0.0], [Vector2(0, 1), Vector2(0, 0), 1.0, 0.0], [Vector2(0, 0), Vector2(0, 1), 0.55, 0.0]]:
		var g := TextureRect.new()
		var gt := GradientTexture2D.new()
		gt.gradient = Gradient.new()
		gt.gradient.set_color(0, Color(BG, dir[2]))
		gt.gradient.set_color(1, Color(BG, dir[3]))
		gt.gradient.set_offset(1, 0.62 if dir[0] == Vector2(0, 0) and dir[1] == Vector2(1, 0) else 0.55)
		gt.fill_from = dir[0]
		gt.fill_to = dir[1]
		g.texture = gt
		g.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		g.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		g.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(g)
	return root


## Rounded artwork: a Panel draws the rounded shape and clips its TextureRect child to
## it (CanvasItem.clip_children), which works with any stretch/crop mode.
static func rounded_art(radius: int, bg: Color = CARD) -> Panel:
	var holder := Panel.new()
	holder.add_theme_stylebox_override("panel", box(bg, Color.TRANSPARENT, radius, 0))
	holder.clip_children = CanvasItem.CLIP_CHILDREN_AND_DRAW
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var tex := TextureRect.new()
	tex.name = "Art"
	tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	tex.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	tex.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(tex)
	return holder


static func fmt_playtime(minutes: int) -> String:
	if minutes <= 0:
		return "—"
	if minutes < 60:
		return "%d мин в игре" % minutes
	return "%d ч в игре" % int(round(minutes / 60.0))


static func fmt_last_played(ts: int) -> String:
	if ts <= 0:
		return "не запускалась"
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
	return {"budget": "Battery", "balanced": "Balanced", "quality": "Quality",
		"autopilot": "Autopilot", "extreme": "Extreme"}.get(mode, mode if mode != "" else "—")
