## Motion for GFG Shell: one place for durations and curves, so every element moves
## the same way. Each animated property keeps one tween (a new move replaces the old
## one instead of fighting it). Everything is short: the shell must never feel slower
## than the controller.
class_name FX
extends RefCounted

const FAST := 0.12
const MED := 0.2
const SLOW := 0.32


## Tween one property, replacing any tween still running on it.
static func to(node: Node, prop: String, value: Variant, dur: float = MED,
		trans: Tween.TransitionType = Tween.TRANS_CUBIC, ease: Tween.EaseType = Tween.EASE_OUT) -> Tween:
	if node == null or not is_instance_valid(node) or not node.is_inside_tree():
		if node != null and is_instance_valid(node):
			node.set_indexed(prop, value)
		return null
	var key := "_fx_" + prop.replace(":", "_")
	var old: Variant = node.get_meta(key) if node.has_meta(key) else null
	if old is Tween and (old as Tween).is_valid():
		(old as Tween).kill()
	var t := node.create_tween()
	t.tween_property(node, prop, value, dur).set_trans(trans).set_ease(ease)
	node.set_meta(key, t)
	return t


## Scale around the centre (keeps the pivot in step with the size).
static func scale_to(c: Control, s: float, dur: float = MED,
		trans: Tween.TransitionType = Tween.TRANS_BACK) -> void:
	c.pivot_offset = c.size / 2.0
	to(c, "scale", Vector2(s, s), dur, trans)


## Focus lift for a control: grows a little on focus and settles back.
static func lift(c: Control, amount: float = 1.04) -> void:
	c.set_meta("fx_focus_scale", amount)
	c.focus_entered.connect(func(): scale_to(c, amount, MED))
	c.focus_exited.connect(func(): scale_to(c, 1.0, FAST, Tween.TRANS_CUBIC))
	c.resized.connect(func(): c.pivot_offset = c.size / 2.0)


## A short squeeze on press (A): the controller press is felt on screen.
static func press(b: BaseButton) -> void:
	b.button_down.connect(func(): scale_to(b, 0.95, 0.06, Tween.TRANS_CUBIC))
	b.button_up.connect(func():
		var rest: float = float(b.get_meta("fx_focus_scale", 1.04)) if b.has_focus() else 1.0
		scale_to(b, rest, MED))


## Fade a control in from a small offset (pages, panels, rows).
static func enter(c: Control, from: Vector2 = Vector2(0, 14), dur: float = MED, delay: float = 0.0) -> void:
	if not c.is_inside_tree():
		return
	var key := "_fx_enter"
	var old: Variant = c.get_meta(key) if c.has_meta(key) else null
	if old is Tween and (old as Tween).is_valid():
		(old as Tween).kill()
	var base: Vector2 = c.get_meta("_fx_base_pos") if c.has_meta("_fx_base_pos") else c.position
	c.set_meta("_fx_base_pos", base)
	c.modulate.a = 0.0
	c.position = base + from
	var t := c.create_tween().set_parallel(true)
	t.tween_property(c, "modulate:a", 1.0, dur).set_delay(delay)
	t.tween_property(c, "position", base, dur * 1.3).set_delay(delay).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	c.set_meta(key, t)
