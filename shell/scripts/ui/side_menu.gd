## Main menu (Menu button), mockup 07: profile card, then Главная / Библиотека /
## Магазин / Друзья / Загрузки / Настройки / GFG Extreme / Питание.
class_name SideMenu
extends Overlay

var _list: VBoxContainer
var _name: Label
var _avatar: TextureRect
var _badge: Label


func _ready() -> void:
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.55)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var p := UI.panel(Color("111116"), 14, 16)
	p.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE)
	p.offset_left = 18
	p.offset_top = 86
	p.offset_bottom = -70
	p.offset_right = 18 + 380
	add_child(p)
	var v := UI.vbox(6)
	p.add_child(v)
	var prof := Button.new()
	prof.focus_mode = Control.FOCUS_ALL
	prof.custom_minimum_size = Vector2(0, 86)
	prof.add_theme_stylebox_override("normal", UI.box(Color(0, 0, 0, 0), Color.TRANSPARENT, 12))
	prof.add_theme_stylebox_override("hover", UI.box(Color(1, 1, 1, 0.04), Color.TRANSPARENT, 12))
	prof.add_theme_stylebox_override("focus", UI.focus_box(UI.RED, 12))
	prof.pressed.connect(func(): close(); OS.create_process(GameRunner.steam_command(), ["steam://open/friends"]))
	var ph := UI.hbox(14)
	ph.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var pm := UI.margin(ph, 12, 8, 12, 8)
	pm.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	pm.mouse_filter = Control.MOUSE_FILTER_IGNORE
	prof.add_child(pm)
	var av := Control.new()
	av.custom_minimum_size = Vector2(60, 60)
	av.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	av.mouse_filter = Control.MOUSE_FILTER_IGNORE
	av.draw.connect(func(): av.draw_circle(av.size / 2, 30, UI.RED_DIM); av.draw_arc(av.size / 2, 29, 0, TAU, 48, UI.RED, 2, true))
	var holder := UI.rounded_art(26, UI.RED_DIM)
	holder.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT, Control.PRESET_MODE_MINSIZE, 4)
	_avatar = holder.get_node("Art")
	av.add_child(holder)
	ph.add_child(av)
	var nv := VBoxContainer.new()
	nv.alignment = BoxContainer.ALIGNMENT_CENTER
	nv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_name = UI.label("", 19, UI.TEXT, "bold")
	nv.add_child(_name)
	nv.add_child(UI.label("В сети", 14, Color("4ea3ff"), "medium"))
	ph.add_child(nv)
	ph.add_child(GIcon.make("chevron", 18, UI.TEXT_DIM))
	v.add_child(prof)
	_list = UI.vbox(4)
	v.add_child(_list)
	var items := [["home", "Главная", "home"], ["library", "Библиотека", "library"], ["store", "Магазин", "store"],
		["friends", "Друзья", "friends"], ["download", "Загрузки", "downloads"], ["settings", "Настройки", "settings"],
		["bolt", "GFG Extreme", "gfg"], ["power", "Питание", "power"]]
	for it in items:
		var b := UI.row(it[0], it[1], "", null, 58)
		b.set_meta("target", it[2])
		b.pressed.connect(_go.bind(it[2]))
		if it[2] == "downloads":
			_badge = UI.label("", 13, UI.TEXT, "bold")
			_badge.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			_badge.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			_badge.custom_minimum_size = Vector2(26, 26)
			_badge.add_theme_stylebox_override("normal", UI.box(UI.RED, Color.TRANSPARENT, 13, 0))
			(b.get_child(0).get_child(0) as HBoxContainer).add_child(_badge)
		_list.add_child(b)


func _on_open() -> void:
	var p := Shell.library.persona()
	_name.text = p.name if p.name != "" else "Steam"
	_avatar.texture = null
	if p.avatar != "":
		Shell.load_art(p.avatar, func(t): _avatar.texture = t)
	var n := Shell.games.filter(func(g): return g.get("update_pending", false)).size()
	_badge.text = str(n)
	_badge.visible = n > 0
	var current: String = app.current_page()
	for b in _list.get_children():
		var active: bool = b.get_meta("target") == current
		b.add_theme_stylebox_override("normal", UI.box(UI.RED if active else Color(0, 0, 0, 0), Color.TRANSPARENT, 10))


func first_focus() -> Control:
	var current: String = app.current_page()
	for b in _list.get_children():
		if b.get_meta("target") == current:
			return b
	return _list.get_child(0)


func _go(target: String) -> void:
	close()
	match target:
		"home", "library", "store":
			app.go_tab(target)
		"friends":
			OS.create_process(GameRunner.steam_command(), ["steam://open/friends"])
		"power":
			app.show_power_menu()
		_:
			app.push(target)
