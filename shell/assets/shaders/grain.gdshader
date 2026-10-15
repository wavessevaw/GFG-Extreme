// Fine animated film grain over the backdrop: keeps dark gradients from banding
// on the 8-bit panel and gives the art a filmic finish. Very low intensity.
shader_type canvas_item;

uniform float amount = 0.035;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec2 cell = floor(FRAGCOORD.xy / 2.0);
	float n = hash(cell + floor(TIME * 24.0) * vec2(1.7, 9.2)) - 0.5;
	COLOR = vec4(vec3(n > 0.0 ? 1.0 : 0.0), abs(n) * 2.0 * amount);
}
