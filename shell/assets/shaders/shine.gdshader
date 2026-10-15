// A soft diagonal band of light that crosses a focused tile once (progress -0.2 -> 1.2).
shader_type canvas_item;

uniform float progress = -1.0;
uniform float width = 0.16;
uniform float strength = 0.32;

void fragment() {
	float d = (UV.x * 0.7 + UV.y * 0.3) - progress;
	float band = smoothstep(width, 0.0, abs(d));
	COLOR = vec4(1.0, 1.0, 1.0, band * strength);
}
