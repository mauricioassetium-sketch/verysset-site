# -*- coding: utf-8 -*-
"""Evidence stream, looping (institutions.html, "Jurisdiction ready / Evidence that survives a supervisor.").

One flat inline SVG on near-black. Three evidence sources (sensor signal, physical condition, legal
record) stream packets into the Verysset core; the core writes each verified record onto a rising
ledger chain; then a supervisor lens inspects the chain block by block, every record holds, and a
shield seal closes the cycle. Loop 10s (loopkit.py):
  0.4 / 1.0 / 1.6s and 3.4 / 4.0 / 4.6s  source packets reach the core (each source flashes as it emits)
  2.3 / 5.4s  scan ring around the core base; the floating core bobs throughout
  2.45-4.8s  a record packet runs up the chain, verifying blocks at 2.8 / 3.25 / 3.7 / 4.15 / 4.6s
  5.6-8.4s  supervisor lens passes over every check (rings at 5.9 .. 7.9s), 8.3s shield seal
  9.1-9.6s  checks and seal clear, 10s loop
Reduced motion or no CSS animation: every block verified, every check and the seal shown, no lens.
"""
import loopkit as lk

T = 10.0
Y, D, K, W = "#FFD400", "#E6BF00", "#0A0A09", "#fff"
EXIT = (9.1, 9.6)
SRC_Y = [88, 170, 252]
CORE = (270, 196)
CHAIN0, CSTEP, CHW, CHH, CT = (362, 250), (34, -17), 16, 8, 14
VERIFY = [2.8 + .45 * k for k in range(5)]
INSPECT = [5.9 + .5 * k for k in range(5)]
ICONS = [
    "M38 {y}H44L47.5 {a}L52 {b}L56 {c}L58 {y}H64",
    "M42 {e}C42 {f} 50 {g} 61 {g}C61 {h} 55 {e} 42 {e}ZM42 {e}L53 {i}",
    "M51 {g}L60 {j}V{k}C60 {l} 56 {m} 51 {n}C46 {m} 42 {l} 42 {k}V{j}ZM47 {o}L50 {p}L55.5 {q}",
]


def _icon(i, y):
    n = lk.num
    return ICONS[i].format(y=y, a=n(y - 8), b=n(y + 9), c=n(y - 4), e=n(y + 9), f=n(y - 4), g=n(y - 10), h=n(y + 1),
                           i=n(y - 2), j=n(y - 6.5), k=n(y + 1), l=n(y + 6), m=n(y + 9.5), n=n(y + 11), o=n(y + .5),
                           p=n(y + 3.5), q=n(y - 2.5))


def _box(cx, yc, hw, hh, t, tints=(".14", ".05", ".09"), stroke_op=".5"):
    top, left, right, outline = lk.iso(cx, yc, hw, hh, t)
    return ('<polygon points="%s %s %s" fill="%s"/><polygon points="%s" fill="%s" fill-opacity="%s"/>'
            '<polygon points="%s" fill="%s" fill-opacity="%s"/><polygon points="%s" fill="%s" fill-opacity="%s"/>'
            '<path d="%s" stroke="%s" stroke-opacity="%s"/>'
            % (top, left, right, K, top, W, tints[0], left, W, tints[1], right, W, tints[2], outline, W, stroke_op))


def svg():
    lp = lk.Loop("js", T, "institutions: jurisdiction evidence stream, loop %gs" % T)
    n = lk.num
    o = ['<svg fill="none" class="lps" viewBox="0 0 560 340" role="img" '
         'aria-label="Jurisdictional alignment of the Verysset verification layer" focusable="false">']
    o.append('<path d="%s" stroke="%s" stroke-opacity=".08" stroke-width="2"/>'
             % ("".join("M%d %dh0" % (x, y) for x in range(20, 560, 36) for y in range(22, 340, 36)), W))

    # evidence sources and their streams into the core
    cx, cy = CORE
    for i, y in enumerate(SRC_Y):
        o.append('<path d="M82 %dL%d %d" stroke="%s" stroke-opacity=".16" stroke-dasharray="2 5"/>' % (y, cx - 74, cy, W))
        o.append('<rect x="28" y="%d" width="46" height="46" rx="6" fill="%s" fill-opacity=".04" stroke="%s" stroke-opacity=".28"/>'
                 % (y - 23, W, W))
        o.append('<rect class="%s" x="28" y="%d" width="46" height="46" rx="6" stroke="%s" stroke-width="1.6" opacity="0"/>'
                 % (lp.flash([.25 + .6 * i, 3.25 + .6 * i], 1, .12, .7), y - 23, Y))
        o.append('<path d="%s" stroke="%s" stroke-opacity=".85" stroke-width="1.5"/>' % (_icon(i, y), W))
        o.append('<circle class="%s" cx="82" cy="%d" r="3.6" fill="%s" opacity="0"/>'
                 % (lp.moves([(.4 + .6 * i, .9), (3.4 + .6 * i, .9)], cx - 74 - 82, cy - y), y, Y))

    # the core: base plate, scan ring, floating verification block with the flat yellow mark, orbit
    o.append(_box(cx, cy, 76, 38, 20))
    o.append('<ellipse class="%s" cx="%d" cy="%d" rx="76" ry="38" stroke="%s" stroke-width="1.5" opacity="0"/>'
             % (lp.rings([2.3, 5.4], 1.0, 1.55, .8), cx, cy, Y))
    o.append('<ellipse cx="%d" cy="150" rx="98" ry="30" stroke="%s" stroke-opacity=".45"/>'
             '<ellipse cx="%d" cy="150" rx="112" ry="36" stroke="%s" stroke-opacity=".16"/>' % (cx, Y, cx, Y))
    bob = lp.frames([(0, "transform:translateY(0px)"), (2.5, "transform:translateY(-7px)"), (5, "transform:translateY(0px)"),
                     (7.5, "transform:translateY(-7px)"), (10, "transform:translateY(0px)")], "ease-in-out")
    top = lk.iso(cx, 124, 58, 29, 22)[0]
    mark = lk.iso(cx, 124, 22, 11, 0)[0]
    o.append('<g class="%s">%s<polygon points="%s" fill="%s"/><polygon points="%s" fill="%s" fill-opacity=".0"/></g>'
             % (bob, _box(cx, 124, 58, 29, 22, (".12", ".05", ".1"), ".7"), mark, Y, top, W))

    # ledger chain, back to front
    (x0, y0), (sx, sy) = CHAIN0, CSTEP
    blocks = [(x0 + sx * k, y0 + sy * k) for k in range(5)]
    o.append('<path d="M%d %dL%d %d" stroke="%s" stroke-opacity=".35" stroke-dasharray="2 4"/>' % (cx + 72, cy + 12, x0, y0 + CHH, Y))
    o.append('<path d="M%d %dL%d %d" stroke="%s" stroke-opacity=".2"/>' % (x0, y0 + CHH, blocks[-1][0], blocks[-1][1] + CHH, W))
    for k in (4, 3, 2, 1, 0):
        bx, by = blocks[k]
        o.append(_box(bx, by, CHW, CHH, CT, stroke_op=".45"))
        o.append('<polygon class="%s" points="%s" fill="%s"/>'
                 % (lp.win(lk.FADE, VERIFY[k] - .05, VERIFY[k] + .2, *EXIT), lk.iso(bx, by, CHW, CHH, CT)[0], Y))
    for k, (bx, by) in enumerate(blocks):
        o.append('<g transform="translate(%d %d)"><circle class="%s" r="7" stroke="%s" stroke-width="1.4" opacity="0"/>'
                 '<g class="%s"><circle r="7" fill="%s"/><path d="M-3.2 .2l2.1 2.1 4.3-4.5" stroke="%s" stroke-width="1.6"/></g></g>'
                 % (bx, by - 22, lp.rings([INSPECT[k]], .7, 2.3), W, lp.win(lk.POP, VERIFY[k], VERIFY[k] + .3, *EXIT), Y, K))

    # record packet: core exit, then up the chain
    sx0, sy0 = cx + 72, cy + 12
    tr = lambda x, y: "transform:translate(%spx,%spx)" % (n(x - sx0), n(y - sy0))
    pts = [(0, "opacity:0;" + tr(sx0, sy0)), (2.45, "opacity:0;" + tr(sx0, sy0)), (2.55, "opacity:1;" + tr(sx0, sy0))]
    pts += [(VERIFY[k], "opacity:1;" + tr(bx, by)) for k, (bx, by) in enumerate(blocks)]
    pts += [(VERIFY[4] + .2, "opacity:0;" + tr(*blocks[4])), (VERIFY[4] + .25, "opacity:0;" + tr(sx0, sy0))]
    o.append('<circle class="%s" cx="%d" cy="%d" r="3.6" fill="%s" opacity="0"/>' % (lp.frames(pts, "linear"), sx0, sy0, Y))

    # supervisor lens: passes over every check, hidden in the static frame
    lx0, ly0 = blocks[0][0], blocks[0][1] - 22
    trl = lambda k: "transform:translate(%spx,%spx)" % (n(sx * k), n(sy * k))
    lens = [(0, "opacity:0;" + trl(0)), (5.55, "opacity:0;" + trl(0)), (5.85, "opacity:1;" + trl(0))]
    lens += [(INSPECT[k], "opacity:1;" + trl(k)) for k in range(5)]
    lens += [(8.25, "opacity:0;" + trl(4)), (8.3, "opacity:0;" + trl(0))]
    o.append('<g transform="translate(%d %d)"><g class="%s" opacity="0"><circle r="21" stroke="%s" stroke-width="1.8"/>'
             '<path d="M15 15L27 27" stroke="%s" stroke-width="3.2"/></g></g>' % (lx0, ly0, lp.frames(lens, lk.EASE), W, W))

    # seal: the evidence survived inspection
    o.append('<g transform="translate(528 104)"><circle class="%s" r="14" stroke="%s" stroke-width="1.5" opacity="0"/>'
             '<g class="%s"><circle r="14" fill="%s"/><path d="M0 -7.5L6 -5V0C6 3.6 3.4 6 0 7.4C-3.4 6 -6 3.6 -6 0V-5Z'
             'M-2.6 -.2L-.7 1.8L2.9 -2" stroke="%s" stroke-width="1.5"/></g></g>'
             % (lp.rings([8.55], 1.0, 2.4), Y, lp.win(lk.POP, 8.3, 8.65, *EXIT), Y, K))
    o.append('<path d="M%d %dL514 114" stroke="%s" stroke-opacity=".4" stroke-dasharray="2 3"/>' % (blocks[4][0] + 6, blocks[4][1] - 30, Y))
    o.append('</svg>')
    return "".join(o)


def figure():
    return '<figure class="lpan" data-loop>%s</figure>' % svg()


if __name__ == "__main__":
    print("jurisdiction svg: %.2f KB, loop %gs" % (len(svg().encode()) / 1024.0, T))
