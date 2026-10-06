# Profile-style original mascot concepts v2 (smooth curves, layered crest outline).
RED, DARK, WHITE, G1, G2 = "#ff3b30", "#0a0a0c", "#f5f5f7", "#1c1c21", "#34343c"

def stroke_layers(paths, scale_group=""):
    out = ""
    for sw, col in ((30, RED), (16, WHITE)):
        out += "".join(f'<path d="{d}" fill="{col}" stroke="{col}" stroke-width="{sw}" stroke-linejoin="round"/>' for d in paths)
    out += "".join(f'<path d="{d}" fill="{DARK}" stroke="{DARK}" stroke-width="2" stroke-linejoin="round"/>' for d in paths)
    return out

def page(body, label):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 480" width="440" height="480">
<rect width="440" height="480" fill="{DARK}"/>{body}
<text x="220" y="452" text-anchor="middle" font-family="DejaVu Sans,Arial,sans-serif" font-weight="900" font-size="60" letter-spacing="4" fill="{WHITE}" stroke="{RED}" stroke-width="2" paint-order="stroke">GFG</text>
<text x="220" y="472" text-anchor="middle" font-family="DejaVu Sans,Arial,sans-serif" font-weight="800" font-size="11" letter-spacing="6" fill="#8a8a93">{label}</text></svg>'''

def wolf():
    mane = "M96,236 L44,214 L78,200 L36,168 L86,172 L60,122 L108,146 L100,96 L136,130 L150,150 L150,250 Z"
    head = ("M84,262 L96,168 L110,96 L136,30 L178,100 "
            "C214,104 246,112 276,130 C312,136 352,158 388,186 C400,196 400,210 388,216 L356,222 "
            "C348,228 344,236 344,246 L300,236 L270,250 C238,244 200,256 160,278 C136,290 112,300 84,262 Z")
    jaw = ("M270,250 L312,268 L356,258 C368,268 364,284 350,294 L306,312 C278,316 252,300 240,276 Z")
    body = stroke_layers([mane, head, jaw])
    detail = (
        f'<path d="M250,146 L306,152 L276,172 L252,166 Z" fill="{RED}"/>'
        f'<path d="M240,140 L312,140 L306,152 L250,146 Z" fill="{WHITE}"/>'
        f'<path d="M128,66 L150,100 L138,128 L122,100 Z" fill="{G2}"/>'
        f'<path d="M180,130 C220,140 250,160 262,200 C230,190 200,170 180,130 Z" fill="{G1}"/>'
        f'<path d="M376,190 L394,200 L380,212 L364,204 Z" fill="{RED}"/>'
        # fangs
        f'<path d="M318,236 L338,240 L332,282 Z" fill="{WHITE}"/><path d="M346,228 L364,226 L358,268 Z" fill="{WHITE}"/>'
        f'<path d="M300,296 L318,290 L310,264 Z" fill="{WHITE}"/>'
        f'<path d="M96,236 L130,214 M84,200 L124,190 M92,160 L130,166" stroke="{RED}" stroke-width="5" stroke-linecap="round"/>')
    return page(f'<g transform="translate(6,36)">{body}{detail}</g>', "WOLF")


for n, f in {"wolf": wolf}.items():
    open(f"logo2-{n}.svg", "w").write(f())
