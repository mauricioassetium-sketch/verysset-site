# -*- coding: utf-8 -*-
"""Evidence that survives a supervisor, looping (institutions.html, "Jurisdiction ready").

Round 7, dark 3D (dark3d.py), the same language as the digital twin on how-it-works: a black
platform on a near-black metallic panel, split by a raised wall into two lanes. The operations
lane (neutral white) carries operational records past, behind the wall, and never reaches custody.
The evidence lane (#FFD400) carries a continuous stream of records into a floating evidence stack,
three matte black ledger slabs wrapped in three concentric glowing rings. A supervisor scan then
rises through the stack and a seal confirms the history holds. Flat SVG, stepped opacity glow, no
gradients or filters. Loop 10s, every part on one cycle (loopkit.py):
  0-10s     evidence records ride their lane twice per cycle (a record lands every 1.67s, the
            stack rim flashes on each landing); operations records ride once, behind the wall
  0-10s     rings turn (inner and outer clockwise, middle counter clockwise), particles orbit
  0.8 / 5.8s  ring glow pulses outward, inner to outer, 0.5s apart
  0-10s     the stack bobs twice (up at 2.5 / 7.5s), the light pool dims as it rises
  6.0-8.0s  supervisor scan frame rises through the three slabs
  8.05s     seal pops above the stack with a sparkle, clears 9.3-9.7s
Reduced motion or no CSS animation: records spread along both lanes, rings lit, seal shown, no scan.
"""
import loopkit as lk
import dark3d as d3

T = 10.0
Y, K, W = d3.Y, d3.K, d3.W
VW, VH = 600, 400
CAM = d3.Cam(290, 212, yaw=24, sp=.45)
PX, PY0, PY1, PT = 226, -134, 92, 22          # platform: half length (world x), y span, thickness
X0 = -196                                     # both lanes start at the intake gates
OPS_Y, OPS_HW, OPS_X1 = -100, 17, 206         # operations lane, runs the full length behind the wall
WALL_Y = -66
EV_Y, EV_HW, EV_X1 = 12, 26, 118              # evidence lane, ends under the stack
STACK, SH, CROT = (140, 12), 42, 16           # evidence stack centre, half size, extra turn
SLABS = [(54, 70), (78, 94), (102, 118)]      # ledger slabs, z ranges (light gap between them)
ZR = 26                                       # ring plane
RINGS = [(64, 360, 4, .17, 2), (84, -360, 3, .28, 1), (104, 360, 2, .1, 2)]
BOB = 7
PULSE = [.8, 5.8]
EV_PHASE = [.12, .45, .78]                    # 3 records, 2 laps: one landing every 1.67s
OPS_PHASE = [.08, .28, .48, .68, .88]         # 5 records, 1 lap
SCAN = (6.0, 8.0)
SEAL = 8.05
EXIT = (9.3, 9.7)


def _strip(x0, x1, y, hw):
    p = CAM.p
    return [p(x0, y - hw), p(x1, y - hw), p(x1, y + hw), p(x0, y + hw)]


def _label(x, y, text, color, op):
    """Upright label skewed along the lanes, anchored on the platform at world (x, y)."""
    sx, sy = CAM.p(x, y)
    return ('<text transform="matrix(1 %s 0 1 %s %s)" fill="%s" fill-opacity="%s" font-size="12" font-weight="600" '
            'letter-spacing="2.4">%s</text>' % (lk.num(CAM.s * CAM.sp / CAM.c, 3), lk.num(sx), lk.num(sy), color, op, text))


def svg():
    lp = lk.Loop("js", T, "institutions: jurisdiction evidence stream, dark 3D, loop %gs" % T)
    n, p = lk.num, CAM.p
    o = ['<svg fill="none" class="lps" viewBox="0 0 %d %d" role="img" '
         'aria-label="Jurisdictional alignment of the Verysset verification layer: evidence and operations kept in '
         'separate lanes" focusable="false">' % (VW, VH)]
    o.append(d3.panel(VW, VH, seams=((200, 400), (133, 267))))
    scx, scy = p(STACK[0], STACK[1], 86)
    o.append(d3.halo(scx, scy + 20))

    # platform
    plat = d3.Box(CAM, 0, (PY0 + PY1) / 2.0, PX, (PY1 - PY0) / 2.0, -PT, 0)
    o.append(plat.svg(tint=(".045", ".03", ".014"), edge=".16", top_edge=".26"))
    inset = d3.Box(CAM, 0, (PY0 + PY1) / 2.0, PX - 14, (PY1 - PY0) / 2.0 - 14, 0, 0)
    o.append('<path d="%s" stroke="%s" stroke-opacity=".06"/>' % (d3.M(inset.top, True), W))

    # operations lane: neutral, full length, behind the wall
    ops = _strip(X0, OPS_X1, OPS_Y, OPS_HW)
    o.append('<polygon points="%s" fill="%s" fill-opacity=".025"/><path d="%s%s" stroke="%s" stroke-opacity=".14"/>'
             '<path d="%s" stroke="%s" stroke-opacity=".1" stroke-dasharray="3 7"/>'
             % (d3.P(ops), W, d3.M(ops[:2]), d3.M(ops[2:]), W, d3.M([p(X0, OPS_Y), p(OPS_X1, OPS_Y)]), W))
    o.append(d3.Box(CAM, X0 - 10, OPS_Y, 4, OPS_HW + 6, 0, 30).svg(tint=(".1", ".06", ".03"), edge=".24", top_edge=".4"))
    dx, dy = p(OPS_X1 - 24, 0)[0] - p(X0 + 12, 0)[0], p(OPS_X1 - 24, 0)[1] - p(X0 + 12, 0)[1]
    for ph in OPS_PHASE:
        cls, _ = d3.stream(lp, ph, dx, dy, laps=1)
        x = X0 + 12 + ph * (OPS_X1 - X0 - 36)
        o.append('<g class="%s">%s</g>' % (cls, d3.Box(CAM, x, OPS_Y, 13, 9, 0, 5).svg(
            tint=(".2", ".1", ".06"), edge=".3", top_edge=".5")))

    # the wall: functional separation, operations never cross into custody
    wall = d3.Box(CAM, (X0 - 16 + PX) / 2.0, WALL_Y, (PX - X0 + 16) / 2.0 - 6, 2.5, 0, 14)
    o.append(wall.svg(tint=(".12", ".07", ".04"), edge=".22", top_edge=".5"))

    # evidence lane: warm, ends in the light pooled under the stack
    ev = _strip(X0, EV_X1, EV_Y, EV_HW)
    o.append('<polygon points="%s" fill="%s" fill-opacity=".035"/>' % (d3.P(ev), Y))
    o.append(d3.glow_path(d3.M(ev[:2]) + d3.M(ev[2:]), ((5, ".04"), (2.4, ".1"), (1, ".45"))))
    o.append('<path d="%s" stroke="%s" stroke-opacity=".3" stroke-width="1.4"/>'
             % ("".join(d3.M([p(x - 5, EV_Y - 9), p(x + 3, EV_Y), p(x - 5, EV_Y + 9)]) for x in range(-150, 80, 46)), Y))
    gate = d3.Box(CAM, X0 - 10, EV_Y, 4, EV_HW + 6, 0, 34)
    o.append(gate.svg(tint=(".1", ".06", ".03"), edge=".24", top_edge=".44") + gate.warm(rim=False))
    dim = lp.frames([(0, "opacity:1"), (2.5, "opacity:.7"), (5, "opacity:1"), (7.5, "opacity:.7"), (10, "opacity:1")],
                    "ease-in-out")
    o.append(d3.pool(CAM, STACK[0], STACK[1], 0, cls=dim))
    dx, dy = p(EV_X1 - 8, 0)[0] - p(X0 + 12, 0)[0], p(EV_X1 - 8, 0)[1] - p(X0 + 12, 0)[1]
    landings = []
    for ph in EV_PHASE:
        cls, arr = d3.stream(lp, ph, dx, dy, laps=2)
        landings += arr
        x = X0 + 12 + ph * (EV_X1 - X0 - 20)
        rec = d3.Box(CAM, x, EV_Y, 16, 12, 0, 7)
        mark = d3.Box(CAM, x, EV_Y, 6, 5, 7, 7).top
        o.append('<g class="%s">%s%s<polygon points="%s" fill="%s"/></g>'
                 % (cls, rec.svg(tint=(".12", ".06", ".03"), edge=".3", top_edge=".2"),
                    d3.glow_path(d3.M(rec.top, True), ((4, ".08"), (2, ".2"), (1, ".8"))), d3.P(mark), Y))
    landings.sort()

    o.append(_label(X0 - 4, EV_Y + EV_HW + 30, "EVIDENCE", Y, ".85"))
    o.append(_label(X0 + 6, PY0 + 2, "OPERATIONS", W, ".5"))

    # the three rings around the stack (back halves pass behind it, drawn after them)
    for i, (r, turn, segs, dash, dots) in enumerate(RINGS):
        pts = [(0, "opacity:.6;transform:scale(1)")]
        for t0 in PULSE:
            t = t0 + .5 * i
            pts += [(t - .3, "opacity:.6;transform:scale(1)"), (t, "opacity:1;transform:scale(1.02)"),
                    (t + 1.5, "opacity:.6;transform:scale(1)")]
        o.append(d3.ring(CAM, lp, STACK[0], STACK[1], ZR, r, turn, segs, dash, lp.frames(pts, "ease-out"), dots))

    # the evidence stack: bobbing ledger slabs, supervisor scan, seal
    bob = lp.frames([(0, "transform:translateY(0px)"), (2.5, "transform:translateY(-%dpx)" % BOB),
                     (5, "transform:translateY(0px)"), (7.5, "transform:translateY(-%dpx)" % BOB),
                     (10, "transform:translateY(0px)")], "ease-in-out")
    o.append('<g class="%s">' % bob)
    frame = d3.Box(CAM, STACK[0], STACK[1], SH + 12, SH + 12, SLABS[0][0] - 6, SLABS[0][0] - 6, CROT)
    lift = (SLABS[-1][1] + 8 - (SLABS[0][0] - 6)) * CAM.cp
    s0, s1 = SCAN
    scan = lp.frames([(0, "opacity:0;transform:translateY(0px)"), (s0, "opacity:0;transform:translateY(0px)"),
                      (s0 + .25, "opacity:1;transform:translateY(0px)"),
                      (s1 - .25, "opacity:1;transform:translateY(-%spx)" % n(lift)),
                      (s1, "opacity:0;transform:translateY(-%spx)" % n(lift)),
                      (s1 + .05, "opacity:0;transform:translateY(0px)")], "linear")
    front = frame.top_front()
    back =[front[2]] + [q for q in frame.top if q not in front] + [front[0]]
    o.append('<g class="%s" opacity="0">%s</g>' % (scan, d3.glow_path(d3.M(back), ((5, ".06"), (2.4, ".14"), (1, ".5")))))
    rim = lp.flash(landings, .9, .12, .7)
    for k, (z0, z1) in enumerate(SLABS):
        slab = d3.Box(CAM, STACK[0], STACK[1], SH, SH, z0, z1, CROT)
        o.append(slab.svg(tint=(".085", ".05", ".024"), edge=".22", top_edge=".46"))
        o.append(slab.warm(bands=((0, .16, ".18"), (.16, .4, ".08")), rim=True))
        if k == 0:
            o.append('<g class="%s" opacity="0">%s</g>' % (rim, d3.glow_path(slab.bottom_edges(), ((10, ".1"), (5, ".25"), (2, "1")))))
    top = d3.Box(CAM, STACK[0], STACK[1], SH, SH, SLABS[-1][1], SLABS[-1][1], CROT)
    seam = d3.Box(CAM, STACK[0], STACK[1], SH - 14, SH - 14, SLABS[-1][1], SLABS[-1][1], CROT)
    mark = d3.Box(CAM, STACK[0], STACK[1], 12, 12, SLABS[-1][1], SLABS[-1][1], CROT)
    o.append('<path d="%s" stroke="%s" stroke-opacity=".1"/><polygon points="%s" fill="%s"/>'
             % (d3.M(seam.top, True), W, d3.P(mark.top), Y))
    o.append('<g class="%s" opacity="0">%s</g>' % (scan, d3.glow_path(d3.M(front), ((6, ".08"), (3, ".2"), (1.4, ".95")))))
    ax, ay = top.apex()
    o.append(d3.sparkle(ax, ay, .9, lp.frames([(0, "opacity:0;transform:scale(0) rotate(0deg)"),
                                              (SEAL + .15, "opacity:0;transform:scale(0) rotate(0deg)"),
                                              (SEAL + .4, "opacity:1;transform:scale(1) rotate(45deg)"),
                                              (SEAL + 1.0, "opacity:0;transform:scale(.3) rotate(90deg)"),
                                              (SEAL + 1.03, "opacity:0;transform:scale(0) rotate(0deg)")], "ease-out")))
    o.append('<g transform="translate(%s %s)"><circle class="%s" r="15" stroke="%s" stroke-width="1.5" opacity="0"/>'
             '<g class="%s"><circle r="22" fill="%s" fill-opacity=".08"/><circle r="15" fill="%s"/>'
             '<path d="M0 -8L6.4 -5.3V0C6.4 3.8 3.6 6.4 0 7.9C-3.6 6.4 -6.4 3.8 -6.4 0V-5.3Z" fill="%s"/>'
             '<path d="M-2.8 -.2L-.8 1.9L3 -2.1" stroke="%s" stroke-width="1.6"/></g></g>'
             % (n(ax + 54), n(ay - 22), lp.rings([SEAL + .2], 1.0, 2.4), Y, lp.win(lk.POP, SEAL, SEAL + .35, *EXIT), Y, Y, K, Y))
    o.append('</g>')
    o.append('</svg>')
    return "".join(o)


def figure():
    return '<figure class="lpan" data-loop>%s</figure>' % svg()


if __name__ == "__main__":
    print("jurisdiction svg: %.2f KB, loop %gs" % (len(svg().encode()) / 1024.0, T))
