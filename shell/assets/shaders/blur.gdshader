// Cheap wide blur for art used as a soft background (a card's fill behind a
// letterboxed header, panel backdrops). 16 taps on a disc; strength in UV.
shader_type canvas_item;

uniform float radius = 0.045;
uniform float dim = 0.55;

void fragment() {
	vec4 acc = vec4(0.0);
	for (int i = 0; i < 16; i++) {
		float a = float(i) * 2.39996;          // golden angle
		float r = sqrt((float(i) + 0.5) / 16.0) * radius;
		acc += texture(TEXTURE, UV + vec2(cos(a), sin(a)) * r);
	}
	acc /= 16.0;
	COLOR = vec4(acc.rgb * dim, 1.0) * COLOR;
}
