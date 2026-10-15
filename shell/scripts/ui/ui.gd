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


## The same face with extra letter spacing, for small uppercase kickers.
static func tracked(weight: String = "semibold", spacing: int = 2) -> Font:
	var key := "%s+%d" % [weight, spacing]
	if _fonts.has(key):
		return _fonts[key]
	var fv := FontVariation.new()
	fv.base_font = font(weight)
	fv.spacing_glyph = spacing
	_fonts[key] = fv
	return fv


## Small uppercase kicker with a short red bar before it ("ПРОДОЛЖИТЬ ИГРУ").
static func kicker(text: String) -> HBoxContainer:
	var h := hbox(10)
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var bar := ColorRect.new()
	bar.color = RED
	bar.custom_minimum_size = Vector2(22, 3)
	bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(bar)
	var l := label(text.to_upper(), 14, TEXT_DIM, "semibold")
	l.name = "Text"
	l.add_theme_font_override("font", tracked("semibold", 2))
	h.add_child(l)
	return h


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


## Focus ring: a thin outline drawn a few pixels outside the control, its corners
## concentric with the control's own (radius = control radius + gap), so it never
## touches or cuts across the fill. `radius` is the control's corner radius.
const FOCUS_GAP := 4


static func focus_box(color: Color = RED, radius: int = RADIUS) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.draw_center = false
	s.set_corner_radius_all(radius + FOCUS_GAP)
	s.corner_detail = 12
	s.set_border_width_all(2)
	s.border_color = color
	s.anti_aliasing = true
	s.anti_aliasing_size = 1.0
	s.expand_margin_left = FOCUS_GAP
	s.expand_margin_right = FOCUS_GAP
	s.expand_margin_top = FOCUS_GAP
	s.expand_margin_bottom = FOCUS_GAP
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
		var fb := focus_box(TEXT)
		fb.shadow_color = Color(RED, 0.5)
		fb.shadow_size = 12
		b.add_theme_stylebox_override("focus", fb)
		_breathe(b, fb)
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


## The primary button's glow breathes while it has the focus.
static func _breathe(b: Button, fb: StyleBoxFlat) -> void:
	var t: Array = [null]
	b.focus_entered.connect(func():
		if t[0] != null and (t[0] as Tween).is_valid():
			(t[0] as Tween).kill()
		var tw := b.create_tween().set_loops()
		tw.tween_property(fb, "shadow_size", 24, 1.1).set_trans(Tween.TRANS_SINE)
		tw.tween_property(fb, "shadow_size", 10, 1.1).set_trans(Tween.TRANS_SINE)
		t[0] = tw)
	b.focus_exited.connect(func():
		if t[0] != null and (t[0] as Tween).is_valid():
			(t[0] as Tween).kill()
		fb.shadow_size = 12)


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
	b.add_theme_stylebox_override("disabled", box(Color(0, 0, 0, 0), Color.TRANSPARENT, 10))
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


## A floating panel (menus, dialogs): a soft shadow lifts it off the page.
static func elevated(p: PanelContainer, shadow: int = 36) -> PanelContainer:
	var sb: StyleBoxFlat = p.get_theme_stylebox("panel")
	sb.shadow_color = Color(0, 0, 0, 0.55)
	sb.shadow_size = shadow
	sb.shadow_offset = Vector2(0, 10)
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


## Full-bleed art with the mockups' darkening: left-to-right and bottom-to-top
## gradients, an edge vignette and a low red bloom from the lower left. Two art
## layers ("Art", "ArtNext") let the app cross-fade between games; both sit in
## "Drift", which the app slowly zooms (a quiet Ken Burns, never distracting).
static func hero_backdrop() -> Control:
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.clip_contents = true
	var drift := Control.new()
	drift.name = "Drift"
	drift.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	# a margin around the screen: the parallax shift never shows an edge
	for side in ["left", "top"]:
		drift.set("offset_" + side, -PARALLAX_PX)
	for side in ["right", "bottom"]:
		drift.set("offset_" + side, PARALLAX_PX)
	drift.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(drift)
	for n in ["Art", "ArtNext"]:
		var tex := TextureRect.new()
		tex.name = n
		tex.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		tex.mouse_filter = Control.MOUSE_FILTER_IGNORE
		if n == "ArtNext":
			tex.modulate.a = 0.0
		drift.add_child(tex)
	for dir in [[Vector2(0, 0), Vector2(1, 0), 0.94, 0.0, 0.66], [Vector2(0, 1), Vector2(0, 0), 1.0, 0.0, 0.6],
			[Vector2(0, 0), Vector2(0, 1), 0.6, 0.0, 0.3]]:
		root.add_child(_gradient_layer(dir[0], dir[1], Color(BG, dir[2]), Color(BG, dir[3]), dir[4]))
	var vig := _gradient_layer(Vector2(0.5, 0.45), Vector2(1.15, 1.1), Color(0, 0, 0, 0.0), Color(0, 0, 0, 0.55), 1.0)
	(vig.texture as GradientTexture2D).fill = GradientTexture2D.FILL_RADIAL
	(vig.texture as GradientTexture2D).gradient.set_offset(0, 0.45)
	root.add_child(vig)
	var bloom := _gradient_layer(Vector2(0.05, 1.05), Vector2(0.75, 0.35), Color(RED, 0.22), Color(RED, 0.0), 1.0)
	(bloom.texture as GradientTexture2D).fill = GradientTexture2D.FILL_RADIAL
	bloom.name = "Bloom"
	root.add_child(bloom)
	# ambient light in the art's own colour, top right (set by the app from the art)
	var glow := _gradient_layer(Vector2(0.92, 0.12), Vector2(0.35, 0.85), Color(RED, 0.0), Color(RED, 0.0), 1.0)
	(glow.texture as GradientTexture2D).fill = GradientTexture2D.FILL_RADIAL
	glow.name = "Glow"
	root.add_child(glow)
	root.add_child(_dust())
	return root


const PARALLAX_PX := 32.0


## Slow bokeh dust over the art: a few dozen soft dots drifting upwards.
static func _dust() -> CPUParticles2D:
	var p := CPUParticles2D.new()
	p.name = "Dust"
	p.amount = 34
	p.lifetime = 16.0
	p.preprocess = 16.0
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(700, 460)
	p.position = Vector2(640, 420)
	p.direction = Vector2(0.15, -1)
	p.spread = 25.0
	p.gravity = Vector2.ZERO
	p.initial_velocity_min = 6.0
	p.initial_velocity_max = 16.0
	p.scale_amount_min = 0.25
	p.scale_amount_max = 1.0
	var gt := GradientTexture2D.new()
	gt.width = 48
	gt.height = 48
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 0.5)
	gt.gradient = Gradient.new()
	gt.gradient.set_color(0, Color(1, 1, 1, 0.9))
	gt.gradient.set_color(1, Color(1, 1, 1, 0.0))
	p.texture = gt
	var ramp := Gradient.new()   # fade in and out over a particle's life
	ramp.set_color(0, Color(1, 1, 1, 0.0))
	ramp.add_point(0.3, Color(1, 1, 1, 0.16))
	ramp.add_point(0.7, Color(1, 1, 1, 0.12))
	ramp.set_color(ramp.get_point_count() - 1, Color(1, 1, 1, 0.0))
	p.color_ramp = ramp
	return p


## The art's ambient colour: a saturated average of its bright pixels (for glows).
static func accent_of(t: Texture2D) -> Color:
	if t == null:
		return RED
	var img := t.get_image()
	if img == null or img.is_empty():
		return RED
	if img.is_compressed():
		img.decompress()
	img.resize(12, 12, Image.INTERPOLATE_BILINEAR)
	var acc := Vector3.ZERO
	var wsum := 0.0
	for y in 12:
		for x in 12:
			var c := img.get_pixel(x, y)
			var w := c.s * c.v + 0.02
			acc += Vector3(c.r, c.g, c.b) * w
			wsum += w
	var a := acc / maxf(wsum, 1e-4)
	var col := Color(a.x, a.y, a.z)
	return Color.from_hsv(col.h, clampf(col.s * 1.3, 0.45, 0.9), 0.95)


static func _gradient_layer(from: Vector2, to: Vector2, c0: Color, c1: Color, end: float) -> TextureRect:
	var g := TextureRect.new()
	var gt := GradientTexture2D.new()
	gt.gradient = Gradient.new()
	gt.gradient.set_color(0, c0)
	gt.gradient.set_color(1, c1)
	gt.gradient.set_offset(1, end)
	gt.fill_from = from
	gt.fill_to = to
	gt.width = 256
	gt.height = 256
	g.texture = gt
	g.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	g.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	g.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return g


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
