## Магазин: the store is Steam's own (purchases, wishlist, keys); the page is a set
## of doors into it over the art of the last game played.
extends Screen

const DOORS := [
	["store", "Магазин", "Рекомендации и новинки", "steam://store"],
	["bolt", "Скидки", "Специальные предложения", "steam://openurl/https://store.steampowered.com/specials/"],
	["star", "Список желаемого", "Игры, которые вы ждёте", "steam://openurl/https://store.steampowered.com/wishlist/"],
	["keyboard", "Активировать ключ", "Код продукта Steam", "steam://open/activateproduct"],
]


func _ready() -> void:
	title = "Магазин"
	var v := UI.vbox(0)
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 52
	v.offset_right = -52
	v.offset_top = 34
	v.offset_bottom = -34
	add_child(v)
	v.add_child(UI.kicker("Steam"))
	var h := UI.label("Магазин", 56, UI.TEXT, "bold")
	h.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.45))
	h.add_theme_constant_override("shadow_offset_y", 3)
	v.add_child(h)
	var l := UI.label("Покупки, скидки и ключи работают в магазине Steam: он открывается поверх GFG Shell, кнопка B возвращает сюда.", 17, UI.TEXT_DIM, "regular")
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(640, 0)
	l.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	v.add_child(l)
	v.add_child(UI.spacer(false))
	var row := UI.hbox(18)
	for d in DOORS:
		row.add_child(_door(d[0], d[1], d[2], d[3]))
	v.add_child(row)


## A large tile: icon, title, subtitle; lifts and glows on focus.
func _door(icon: String, t: String, sub: String, url: String) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.custom_minimum_size = Vector2(0, 210)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var normal := UI.box(Color(0.07, 0.07, 0.09, 0.86), UI.LINE, 16)
	b.add_theme_stylebox_override("normal", normal)
	b.add_theme_stylebox_override("hover", UI.box(Color(0.1, 0.1, 0.12, 0.9), UI.LINE, 16))
	b.add_theme_stylebox_override("pressed", normal)
	var fb := UI.focus_box(UI.RED, 16)
	fb.bg_color = Color(0.09, 0.08, 0.1, 0.92)
	fb.draw_center = true
	fb.shadow_color = Color(UI.RED, 0.35)
	fb.shadow_size = 18
	b.add_theme_stylebox_override("focus", fb)
	var col := UI.vbox(6)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var m := UI.margin(col, 24, 24, 24, 22)
	m.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	m.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(m)
	var disc := Panel.new()
	disc.custom_minimum_size = Vector2(52, 52)
	disc.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	disc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	disc.add_theme_stylebox_override("panel", UI.box(Color(UI.RED, 0.16), Color.TRANSPARENT, 26))
	var ic := GIcon.make(icon, 24, UI.RED.lightened(0.25))
	ic.position = Vector2(14, 14)
	disc.add_child(ic)
	col.add_child(disc)
	col.add_child(UI.spacer(false))
	col.add_child(UI.label(t, 21, UI.TEXT, "bold"))
	col.add_child(UI.label(sub, 15, UI.TEXT_DIM, "medium"))
	b.pressed.connect(func(): OS.create_process(GameRunner.steam_command(), [url]))
	FX.lift(b, 1.04)
	FX.press(b)
	return b


func enter(_args: Dictionary = {}) -> void:
	var recent := Shell.recent_games(1)
	if not recent.is_empty():
		var art: Dictionary = recent[0].get("art", {})
		app.set_backdrop(art.get("hero", art.get("header", "")), 0.55)


func focus_default() -> void:
	super.focus_default()
