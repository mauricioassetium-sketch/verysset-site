# -*- coding: utf-8 -*-
"""The verifiable digital twin, looping (how-it-works.html, "The asset, mirrored by its own evidence.").

Round 7, dark 3D (dark3d.py): a matte black cube, the twin, floats over a black platform. Three
concentric #FFD400 rings circle it in the plane of the light gap, a protective aura and the
verification cycle. Warm light pools where cube meets platform, its lit footprint mirrors the cube.
Flat SVG, stepped opacity glow, no gradients or filters. Loop 9s, every part on one cycle (loopkit.py):
  0-9s      rings turn (inner and outer clockwise, middle counter clockwise), particles orbit on them
  0.3 / 4.8s  a processing wave leaves the core and crosses all three rings
  0.6 / 5.1s  ring glow pulses outward, inner to outer, 0.5s apart
  0-9s      the cube bobs twice (up at 2.25 / 6.75s), the light pool and the lit
            footprint dim as the cube rises
  2.0 / 6.5s  a glint runs along the top edges, then a sparkle at the top corner (2.7 / 7.2s)
  0.2-2.6s and 4.7-7.1s  evidence motes rise from the platform into the gap
Reduced motion or no CSS animation: the markup is the composed scene, rings lit, no glint.
"""
import loopkit as lk
import dark3d as d3

T = 9.0
Y, K, W = d3.Y, d3.K, d3.W
VW, VH = 600, 470
CAM = d3.Cam(300, 306, yaw=24, sp=.45)
PLAT = 176                       # platform half size, top at z 0
PT = 24                          # platform thickness
CUBE, CROT = 58, 16              # cube half size, extra turn over the camera yaw
Z0 = 86                          # cube floats from Z0 to Z0 + 2 * CUBE
ZR = 36                          # ring plane
RINGS = [(110, 360, 4, .17, 2), (138, -360, 3, .28, 1), (166, 360, 2, .1, 2)]   # radius, turn, segments, dash, dots
BOB = 8
PULSE = [.6, 5.1]
WAVES = [.3, 4.8]
SWEEP = [2.0, 6.5]
MOTES = [(-34, 30, .2), (46, 22, .7), (-78, -4, 1.3), (12, 58, 1.9), (84, 36, 2.6)]   # world x, y, first start


def svg():
    lp = lk.Loop("mr", T, "how-it-works: verifiable digital twin, dark 3D, loop %gs" % T)
    n = lk.num
    o = ['<svg fill="none" class="lps" viewBox="0 0 %d %d" role="img" aria-label="Verifiable digital twin of a real world asset" '
         'focusable="false">' % (VW, VH)]
    o.append(d3.panel(VW, VH))
    cube = d3.Box(CAM, 0, 0, CUBE, CUBE, Z0, Z0 + 2 * CUBE, CROT)
    ccx, ccy = CAM.p(0, 0, Z0 + CUBE)
    o.append(d3.halo(ccx, ccy + 30))

    # platform
    plat = d3.Box(CAM, 0, 0, PLAT, PLAT, -PT, 0)
    o.append(plat.svg(tint=(".045", ".03", ".014"), edge=".16", top_edge=".26"))
    inset = d3.Box(CAM, 0, 0, PLAT - 18, PLAT - 18, 0, 0)
    o.append('<path d="%s" stroke="%s" stroke-opacity=".07"/>' % (d3.M(inset.top, True), W))

    # warm pool where the light leaves the core, and the cube mirrored as a lit footprint on the platform
    dim = lp.frames([(0, "opacity:1"), (2.25, "opacity:.7"), (4.5, "opacity:1"), (6.75, "opacity:.7"), (9, "opacity:1")],
                    "ease-in-out")
    o.append(d3.pool(CAM, 0, 0, 0, cls=dim))
    foot = d3.Box(CAM, 0, 0, CUBE, CUBE, 0, 0, CROT).top
    o.append('<g class="%s"><polygon points="%s" fill="%s" fill-opacity=".05"/>%s</g>'
             % (dim, d3.P(foot), Y, d3.glow_path(d3.M(foot, True), ((6, ".05"), (3, ".12"), (1.2, ".5")))))

    # processing wave, lying in the ring plane
    o.append(CAM.plane(0, 0, ZR) + '<circle class="%s" r="52" stroke="%s" stroke-width="1.6" vector-effect="non-scaling-stroke" '
             'opacity="0"/></g>' % (lp.rings(WAVES, 1.9, 3.2, .8), Y))

    # the three rings (the back halves pass behind the cube, which is drawn after them)
    for i, (r, turn, segs, dash, dots) in enumerate(RINGS):
        pts = [(0, "opacity:.6;transform:scale(1)")]
        for p in PULSE:
            t = p + .5 * i
            pts += [(t - .3, "opacity:.6;transform:scale(1)"), (t, "opacity:1;transform:scale(1.02)"),
                    (t + 1.5, "opacity:.6;transform:scale(1)")]
        o.append(d3.ring(CAM, lp, 0, 0, ZR, r, turn, segs, dash, lp.frames(pts, "ease-out"), dots))

    # the twin: floating matte cube, warm underside, glint and sparkle, all bobbing together
    bob = lp.frames([(0, "transform:translateY(0px)"), (2.25, "transform:translateY(-%dpx)" % BOB),
                     (4.5, "transform:translateY(0px)"), (6.75, "transform:translateY(-%dpx)" % BOB),
                     (9, "transform:translateY(0px)")], "ease-in-out")
    o.append('<g class="%s">' % bob)
    o.append(cube.svg(tint=(".085", ".05", ".024"), edge=".22", top_edge=".46"))
    o.append(cube.warm())
    # engraved seam on the top face: the twin is layered, not solid
    mid = d3.Box(CAM, 0, 0, CUBE - 16, CUBE - 16, 0, Z0 + 2 * CUBE, CROT)
    o.append('<path d="%s" stroke="%s" stroke-opacity=".1"/>' % (d3.M(mid.top, True), W))
    sw = []
    for t in SWEEP:
        sw += [(t, "opacity:0;stroke-dashoffset:.2"), (t + .05, "opacity:1;stroke-dashoffset:.2"),
               (t + .75, "opacity:1;stroke-dashoffset:-1"), (t + .8, "opacity:0;stroke-dashoffset:-1"),
               (t + .83, "opacity:0;stroke-dashoffset:.2")]
    o.append('<path class="%s" pathLength="1" stroke-dasharray=".2 1.4" d="%s" stroke="%s" stroke-width="2.2" opacity="0"/>'
             % (lp.frames([(0, "opacity:0;stroke-dashoffset:.2")] + sw, "linear"), d3.M(cube.top_front()), W))
    ax, ay = cube.apex()
    sp = [(0, "opacity:0;transform:scale(0) rotate(0deg)")]
    for t in SWEEP:
        sp += [(t + .6, "opacity:0;transform:scale(0) rotate(0deg)"), (t + .85, "opacity:1;transform:scale(1) rotate(45deg)"),
               (t + 1.4, "opacity:0;transform:scale(.3) rotate(90deg)"), (t + 1.43, "opacity:0;transform:scale(0) rotate(0deg)")]
    o.append(d3.sparkle(ax, ay, 1.0, lp.frames(sp, "ease-out")))
    o.append('</g>')

    # evidence motes rising through the light gap, in front of the cube
    for x, y, t0 in MOTES:
        mx, my = CAM.p(x, y, 4)
        o.append('<g class="%s" opacity="0"><circle cx="%s" cy="%s" r="5" fill="%s" fill-opacity=".22"/>'
                 '<rect x="%s" y="%s" width="3.4" height="3.4" fill="%s"/></g>'
                 % (lp.moves([(t0, 1.7), (t0 + 4.5, 1.7)], 0, -46, .22), n(mx), n(my), Y, n(mx - 1.7), n(my - 1.7), Y))
    o.append('</svg>')
    return "".join(o)


def figure():
    return '<figure class="lpan" data-loop>%s</figure>' % svg()


if __name__ == "__main__":
    s = svg()
    print("mirror svg: %.2f KB, loop %gs" % (len(s.encode()) / 1024.0, T))
