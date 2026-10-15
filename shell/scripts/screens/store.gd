## Магазин: the store is Steam's own (purchases, wishlist, keys); the tab opens it.
extends Screen


func _ready() -> void:
	title = "Магазин"
	var v := UI.vbox(18)
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 52
	v.offset_right = -52
	v.offset_top = 30
	add_child(v)
	v.add_child(UI.label("Магазин Steam", 44, UI.TEXT, "bold"))
	var l := UI.label("Покупки, список желаемого, скидки и активация ключей работают в магазине Steam. GFG Shell открывает его поверх себя; закройте магазин кнопкой B, чтобы вернуться.", 17, UI.TEXT_DIM, "regular")
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(760, 0)
	v.add_child(l)
	var row := UI.hbox(14)
	var open := UI.button("Открыть магазин", true, 280, 64, "store")
	open.pressed.connect(func(): OS.create_process(GameRunner.steam_command(), ["steam://store"]))
	row.add_child(open)
	var wish := UI.button("Список желаемого", false, 280, 64, "star")
	wish.pressed.connect(func(): OS.create_process(GameRunner.steam_command(), ["steam://openurl/https://store.steampowered.com/wishlist/"]))
	row.add_child(wish)
	v.add_child(row)


func focus_default() -> void:
	super.focus_default()
