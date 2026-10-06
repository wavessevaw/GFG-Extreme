# Original GFG mascot logo concepts (not derived from any existing team/brand logo).
RED, DARK, WHITE, GREY = "#ff3b30", "#0a0a0c", "#f5f5f7", "#2a2a31"

def mirrored(half, **attrs):
    a = " ".join(f'{k.replace("_","-")}="{v}"' for k, v in attrs.items())
    return (f'<path d="{half}" {a}/><path d="{half}" transform="translate(400,0) scale(-1,1)" {a}/>')

def badge(body, name, sub="GOOD FRAMES · GREAT FLOW"):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 470" width="400" height="470">
<rect width="400" height="470" fill="{DARK}"/>
{body}
<text x="200" y="440" text-anchor="middle" font-family="DejaVu Sans,Arial,sans-serif" font-weight="900" font-size="60" letter-spacing="4" fill="{WHITE}" stroke="{RED}" stroke-width="2" paint-order="stroke">GFG</text>
<text x="200" y="462" text-anchor="middle" font-family="Arial Black,sans-serif" font-size="11" letter-spacing="5" fill="#9a9aa3">{name}</text>
</svg>'''

def layered(shape_fn):
    """Thick red+white outline under black body — classic sports crest build-up."""
    return (shape_fn(fill="none", stroke=RED, stroke_width=26, stroke_linejoin="round") +
            shape_fn(fill="none", stroke=WHITE, stroke_width=14, stroke_linejoin="round") +
            shape_fn(fill=DARK, stroke=DARK, stroke_width=2, stroke_linejoin="round"))

# 1 ---- WOLF
wolf_half = "M200,104 L226,78 L246,22 L284,92 L324,112 L304,164 L336,206 L292,214 L300,258 L250,252 L228,300 L214,340 L200,352 Z"
def wolf():
    head = layered(lambda **k: mirrored(wolf_half, **k))
    detail = (
        mirrored("M236,150 L290,156 L244,182 Z", fill=RED) +
        mirrored("M200,120 L216,152 L206,186 L200,196 Z", fill=GREY) +
        mirrored("M270,220 L292,232 L262,246 Z", fill=GREY) +
        mirrored("M214,300 L232,298 L224,336 Z", fill=WHITE) +
        f'<path d="M184,286 L216,286 L200,312 Z" fill="{RED}"/>' +
        mirrored("M226,300 L260,282", fill="none", stroke=WHITE, stroke_width=3))
    return badge(f'<g transform="translate(0,6)">{head}{detail}</g>', "WOLF PACK")

# 2 ---- VIPER
hood_half = "M200,50 L270,66 L330,122 L350,206 L316,286 L256,338 L226,384 L200,398 Z"
head_half = "M200,150 L252,176 L246,238 L220,268 L200,274 Z"
def viper():
    hood = layered(lambda **k: mirrored(hood_half, **k))
    d = (mirrored("M200,70 L240,90 L214,138 Z", fill=RED) +
         mirrored("M262,150 L316,190 L296,244 L280,206 Z", fill=GREY) +
         mirrored(head_half, fill="#3a3a42", stroke=WHITE, stroke_width=4, stroke_linejoin="round") +
         mirrored("M222,190 L252,186 L240,206 Z", fill=RED) +
         mirrored("M208,262 L214,330 L222,262 Z", fill=WHITE) +
         f'<path d="M190,236 L210,236 L200,248 Z" fill="{RED}"/>' +
         f'<path d="M196,274 L200,330 L204,274 Z" fill="{RED}"/>')
    return badge(f'<g transform="translate(30,6) scale(0.85)">{hood}{d}</g>', "VIPER")

# 3 ---- RAPTOR (profile, facing right)
def raptor():
    body = "M60,340 L58,214 L96,134 L170,84 L252,76 L312,104 L352,150 L376,200 L366,244 L332,226 L306,204 L296,250 L254,282 L222,340 Z"
    shape = lambda **k: f'<path d="{body}" ' + " ".join(f'{a.replace("_","-")}="{b}"' for a, b in k.items()) + "/>"
    head = layered(shape)
    d = (f'<path d="M214,150 L318,128 L286,176 L238,186 Z" fill="{RED}"/>' +
         f'<path d="M206,132 L330,104 L322,122 L214,150 Z" fill="{WHITE}"/>' +
         f'<path d="M356,196 L376,200 L366,244 L332,226 L346,206 Z" fill="{WHITE}"/>' +
         f'<path d="M70,214 L110,150 L150,206 L112,240 Z" fill="{GREY}"/>' +
         f'<path d="M96,262 L160,224 L200,262 L150,300 Z" fill="{GREY}"/>' +
         f'<path d="M118,110 L176,64 L204,44 L196,88 Z" fill="{RED}"/>')
    return badge(f'<g transform="translate(0,16)">{head}{d}</g>', "RAPTOR")

# 4 ---- BULL
horn_half = "M244,132 L292,128 L326,100 L338,56 L346,10 L370,58 L366,120 L328,170 L276,182 Z"
face_half = "M200,108 L248,118 L270,160 L262,222 L246,262 L236,312 L214,344 L200,350 Z"
def bull():
    horns = layered(lambda **k: mirrored(horn_half, **k))
    face = layered(lambda **k: mirrored(face_half, **k))
    d = (mirrored("M232,168 L288,176 L248,198 Z", fill=RED) +
         mirrored("M200,116 L222,150 L204,196 L200,204 Z", fill=GREY) +
         mirrored("M252,262 L274,230 L282,278 L250,296 Z", fill=GREY) +
         f'<ellipse cx="200" cy="318" rx="34" ry="14" fill="{GREY}"/>' +
         f'<circle cx="188" cy="318" r="5" fill="{RED}"/><circle cx="212" cy="318" r="5" fill="{RED}"/>' +
         f'<path d="M172,334 Q200,380 228,334" fill="none" stroke="{WHITE}" stroke-width="6" stroke-linecap="round"/>')
    return badge(f'<g transform="translate(16,16) scale(0.92)">{horns}{face}{d}</g>', "BULL")

for name, fn in {"wolf": wolf, "viper": viper, "bull": bull}.items():
    open(f"logo-{name}.svg", "w").write(fn())
print("ok")
