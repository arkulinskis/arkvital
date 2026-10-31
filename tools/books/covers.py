"""Front and back covers for the books, as HTML + inline SVG.

Each cover is drawn in a 576 x 864 px box (6 x 9 in at 96 px/in), so the same
markup is the first and last page of the PDF and, screenshotted, the web image.
"""
import math

W, H = 576, 864


def _wedge(vx, vy, ax, ay, bx, by, r):
    """Filled angle marker at vertex v, between the edges toward a and b."""
    a1 = math.atan2(ay - vy, ax - vx)
    a2 = math.atan2(by - vy, bx - vx)
    d = (a2 - a1) % (2 * math.pi)
    if d > math.pi:
        a1, a2 = a2, a1
        d = 2 * math.pi - d
    x1, y1 = vx + r * math.cos(a1), vy + r * math.sin(a1)
    x2, y2 = vx + r * math.cos(a2), vy + r * math.sin(a2)
    mid = a1 + d / 2
    return (f"M{vx:.1f},{vy:.1f} L{x1:.1f},{y1:.1f} A{r},{r} 0 0 1 {x2:.1f},{y2:.1f} Z",
            vx + (r + 22) * math.cos(mid), vy + (r + 22) * math.sin(mid), math.degrees(d))


def _graph_paper(color, step=24):
    lines = []
    for x in range(0, W + 1, step):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}"/>')
    for y in range(0, H + 1, step):
        lines.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}"/>')
    return f'<g stroke="{color}" stroke-width="0.6">{"".join(lines)}</g>'


# --------------------------------------------------------------------------
# Adds Up to 180: cream graph paper, a drawn triangle, three coloured angles.
# --------------------------------------------------------------------------
C180 = dict(paper="#f4ecdc", ink="#2b2420", red="#b9512d", gold="#d49a2a", teal="#2e6e68", soft="#8b7f72")


def art_180():
    c = C180
    P = [(70, 706), (506, 706), (338, 392)]          # Achievement, Appreciation, Hope
    cols = [c["red"], c["gold"], c["teal"]]
    labels = ["A", "A", "H"]
    wedges = []
    for i, (vx, vy) in enumerate(P):
        a, b = P[(i + 1) % 3], P[(i + 2) % 3]
        path, lx, ly, _ = _wedge(vx, vy, *a, *b, 58)
        wedges.append(f'<path d="{path}" fill="{cols[i]}" opacity=".9"/>'
                      f'<text x="{lx:.1f}" y="{ly + 9:.1f}" text-anchor="middle" class="cv180-angle" fill="{cols[i]}">{labels[i]}</text>')
    tri = " ".join(f"{x},{y}" for x, y in P)
    # a second, slightly offset stroke makes it look drawn by hand
    tri2 = " ".join(f"{x + dx},{y + dy}" for (x, y), (dx, dy) in zip(P, [(2, -1), (-2, 2), (1, 2)]))
    return f'''<svg class="cv-art" viewBox="0 0 {W} {H}" aria-hidden="true">
  <rect width="{W}" height="{H}" fill="{c['paper']}"/>
  {_graph_paper('#d9cbb2')}
  <rect x="18" y="18" width="{W - 36}" height="{H - 36}" fill="none" stroke="{c['ink']}" stroke-width="1" opacity=".25"/>
  <g>{''.join(wedges)}</g>
  <polygon points="{tri}" fill="none" stroke="{c['ink']}" stroke-width="3.2" stroke-linejoin="round"/>
  <polygon points="{tri2}" fill="none" stroke="{c['ink']}" stroke-width="1" stroke-linejoin="round" opacity=".45"/>
  <text x="288" y="770" text-anchor="middle" class="cv180-sum" fill="{c['soft']}">A + A + H = 180°</text>
</svg>'''


def front_180(b):
    return f'''<div class="cover cv180">{art_180()}
  <div class="cv-copy">
    <p class="cv-kicker">Achievement · Appreciation · Hope</p>
    <h1 class="cv-title"><span class="l1">Adds Up <i>to</i></span><span class="l2">180<sup>°</sup></span></h1>
    <p class="cv-author">{b['author_cover']}</p>
  </div>
</div>'''


# --------------------------------------------------------------------------
# Addicted to Hope: night sky, one bright star over the summit, a lit tent at
# base camp and a trail that is only drawn part of the way up.
# --------------------------------------------------------------------------
CHOPE = dict(night="#0e1828", dusk="#d98b5f", gold="#f2b552", cream="#f6eedf", ridge="#1a2a44")


def art_hope():
    c = CHOPE
    stars = []
    import random
    rnd = random.Random(7)
    for _ in range(70):
        x, y = rnd.uniform(20, W - 20), rnd.uniform(20, 470)
        r = rnd.choice([0.6, 0.8, 0.8, 1.1, 1.4])
        o = rnd.uniform(.35, .9)
        stars.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" opacity="{o:.2f}"/>')
    trail = [(132, 742), (214, 712), (172, 676), (262, 640), (226, 600), (300, 560), (278, 520), (330, 470)]
    done = " ".join(f"{x},{y}" for x, y in trail[:4])
    todo = " ".join(f"{x},{y}" for x, y in trail[3:])
    return f'''<svg class="cv-art" viewBox="0 0 {W} {H}" aria-hidden="true">
  <defs>
    <linearGradient id="hsky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0a1220"/><stop offset=".42" stop-color="#17253f"/>
      <stop offset=".6" stop-color="#3f3d60"/><stop offset=".72" stop-color="{c['dusk']}"/>
    </linearGradient>
    <linearGradient id="hpeak" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1a2843"/><stop offset="1" stop-color="#0c1526"/>
    </linearGradient>
    <radialGradient id="hglow" cx=".5" cy=".5" r=".5">
      <stop offset="0" stop-color="#fff6dc" stop-opacity="1"/><stop offset=".18" stop-color="{c['gold']}" stop-opacity=".75"/>
      <stop offset="1" stop-color="{c['gold']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="htent" cx=".5" cy=".7" r=".6">
      <stop offset="0" stop-color="#ffd27a"/><stop offset="1" stop-color="#e0893c"/>
    </radialGradient>
    <linearGradient id="hfade" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="{c['gold']}" stop-opacity=".9"/><stop offset="1" stop-color="{c['gold']}" stop-opacity=".15"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#hsky)"/>
  <g>{''.join(stars)}</g>
  <circle cx="338" cy="356" r="92" fill="url(#hglow)"/>
  <path d="M338,336 L343,351 L358,356 L343,361 L338,376 L333,361 L318,356 L333,351 Z" fill="#fffaf0"/>
  <path d="M0,640 L70,596 L130,620 L200,566 L250,592 L420,590 L488,550 L576,598 L576,{H} L0,{H} Z" fill="#4b4467"/>
  <path d="M-10,{H} L60,700 L150,650 L250,520 L330,452 L400,520 L470,570 L586,690 L586,{H} Z" fill="url(#hpeak)"/>
  <path d="M330,452 L400,520 L470,570 L586,690 L586,{H} L520,{H} L430,580 L372,520 Z" fill="#060c18" opacity=".45"/>
  <path d="M250,520 L330,452 L400,520 L470,570" fill="none" stroke="{c['gold']}" stroke-width="1.1" opacity=".55"/>
  <path d="M330,452 L304,474 L316,473 L309,487 L327,477 L339,489 L345,475 L355,476 Z" fill="#dfe5f0"/>
  <path d="M-10,{H} L0,760 L90,730 L180,760 L300,735 L420,770 L586,740 L586,{H} Z" fill="#0b1322"/>
  <polyline points="{done}" fill="none" stroke="{c['gold']}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>
  <polyline points="{todo}" fill="none" stroke="url(#hfade)" stroke-width="2" stroke-dasharray="3 7" stroke-linecap="round"/>
  <path d="M106,756 L132,724 L158,756 Z" fill="url(#htent)"/>
  <path d="M132,724 L132,756" stroke="#7a3f18" stroke-width="1.2"/>
  <ellipse cx="132" cy="760" rx="48" ry="6" fill="{c['gold']}" opacity=".18"/>
</svg>'''


def front_hope(b):
    return f'''<div class="cover cvhope">{art_hope()}
  <div class="cv-copy">
    <h1 class="cv-title"><span class="l1">Addicted</span><span class="l2">to <i>Hope</i></span></h1>
    <p class="cv-sub">Why dreaming feels better than doing,<br>and how to ship your life anyway</p>
    <p class="cv-author">{b['author_cover']}</p>
  </div>
</div>'''


def back_cover(b, other):
    paras = "".join(f"<p>{p}</p>" for p in b["blurb"])
    kind = "cv180" if b["slug"] == "adds-up-to-180" else "cvhope"
    bg = ('<svg class="cv-art" viewBox="0 0 576 864" aria-hidden="true"><rect width="576" height="864" fill="#f4ecdc"/>'
          + _graph_paper('#e2d6c0') + '</svg>') if kind == "cv180" else \
         ('<svg class="cv-art" viewBox="0 0 576 864" aria-hidden="true"><defs><linearGradient id="hb" x1="0" y1="0" x2="0" y2="1">'
          '<stop offset="0" stop-color="#0a1220"/><stop offset="1" stop-color="#1d2a45"/></linearGradient></defs>'
          '<rect width="576" height="864" fill="url(#hb)"/></svg>')
    return f'''<div class="cover back {kind}">{bg}
  <div class="back-copy">
    <p class="back-tag">{b['tagline']}</p>
    <div class="back-blurb">{paras}</div>
    <div class="back-foot">
      <div><p class="back-also">Also by {b['author_cover'].title()}</p><p class="back-other">{other['title']}</p></div>
      <div class="back-site"><p>Free PDF edition</p><p><b>arkvital.com</b></p></div>
    </div>
  </div>
</div>'''


FRONTS = {"adds-up-to-180": front_180, "addicted-to-hope": front_hope}

COVER_CSS = """
.cover{position:relative;width:576px;height:864px;overflow:hidden;break-after:page;page:cover}
.cover .cv-art{position:absolute;inset:0;width:100%;height:100%;display:block}
.cover .cv-copy,.cover .back-copy{position:absolute;inset:0}
.cv-author{position:absolute;left:0;right:0;bottom:44px;margin:0;text-align:center;font:600 13px/1 Inter;letter-spacing:.42em;text-indent:.42em}
.cv-title{margin:0;font-weight:400}
.cv-title span{display:block}

.cv180{color:#2b2420}
.cv180 .cv-kicker{position:absolute;top:58px;left:0;right:0;margin:0;text-align:center;font:600 10.5px/1 Inter;letter-spacing:.3em;text-transform:uppercase;color:#8b7f72}
.cv180 .cv-title{position:absolute;top:86px;left:0;right:0;text-align:center;font-family:Fraunces}
.cv180 .cv-title .l1{font-size:58px;line-height:1;letter-spacing:-.01em;font-variation-settings:"SOFT" 100,"opsz" 144;font-weight:500}
.cv180 .cv-title .l1 i{font-weight:300;font-style:italic}
.cv180 .cv-title .l2{font-size:178px;line-height:.9;font-weight:700;letter-spacing:-.04em;color:#b9512d;font-variation-settings:"SOFT" 50,"opsz" 144,"WONK" 1;margin-top:4px}
.cv180 .cv-title sup{font-size:.4em;vertical-align:.95em;font-weight:500;margin-left:2px}
.cv180 .cv-sub{position:absolute;top:792px;left:0;right:0;margin:0;text-align:center;font:italic 300 14px/1.35 Fraunces;color:#5b5047;display:none}
.cv180 .cv-author{color:#2b2420}
.cv180-angle{font:700 30px Fraunces}
.cv180-sum{font:500 13px Inter;letter-spacing:.18em}

.cvhope{color:#f6eedf}
.cvhope .cv-title{position:absolute;top:70px;left:0;right:0;text-align:center;font-family:Fraunces}
.cvhope .cv-title .l1{font-size:76px;line-height:1;font-weight:600;letter-spacing:-.025em;font-variation-settings:"SOFT" 100,"opsz" 144}
.cvhope .cv-title .l2{font-size:66px;line-height:1.05;font-weight:300;letter-spacing:-.02em;font-variation-settings:"SOFT" 100,"opsz" 144}
.cvhope .cv-title .l2 i{font-weight:600;color:#f2b552;font-size:1.25em}
.cvhope .cv-sub{position:absolute;top:258px;left:0;right:0;margin:0;text-align:center;font:400 13.5px/1.5 Inter;letter-spacing:.02em;color:#cdd5e4}
.cvhope .cv-author{color:#f6eedf}

.back .back-copy{padding:70px 62px 0;box-sizing:border-box}
.back-tag{margin:0 0 26px;font:600 25px/1.2 Fraunces;letter-spacing:-.01em;font-variation-settings:"SOFT" 100,"opsz" 72}
.back-blurb p{margin:0 0 12px;font:400 12.6px/1.6 Literata}
.back-foot{position:absolute;left:62px;right:62px;bottom:56px;display:flex;justify-content:space-between;align-items:flex-end;padding-top:16px;border-top:1px solid currentColor}
.back-foot p{margin:0}
.back-also{font:600 9px/1.4 Inter;letter-spacing:.2em;text-transform:uppercase;opacity:.75}
.back-other{font:italic 500 16px/1.3 Fraunces}
.back-site{text-align:right;font:500 10.5px/1.6 Inter;letter-spacing:.06em}
.back.cv180{color:#2b2420}.back.cv180 .back-tag{color:#b9512d}
.back.cvhope{color:#eef1f7}.back.cvhope .back-tag{color:#f2b552}
"""
