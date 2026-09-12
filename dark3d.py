# -*- coding: utf-8 -*-
"""Dark 3D vocabulary for the round 7 looping illustrations (mirror.py, jurisdiction.py).

A premium dark scene built from flat SVG only: a matte black floating cube or stack over a black
platform, three concentric #FFD400 rings, warm light pooled where the object meets the platform,
on a near-black metallic panel. No gradients, no blur, no filters: every glow is a few flat copies
of the same shape at stepped opacity. Everything animated goes through loopkit.py (transform and
opacity only), so reduced motion still shows the fully composed scene.

Projection: an orthographic camera with a yaw (the plan is turned, so the two visible faces differ)
and a pitch given by sp = sin(pitch). World z is up. A circle lying in a horizontal plane is drawn
as a circle inside <g transform="translate() scale(1 sp)">, which is exactly its projection, so a
CSS rotate on the inner circle turns it in its own plane.
"""
import math
import loopkit as lk

Y, K, W = "#FFD400", "#0A0A09", "#fff"
n = lk.num


class Cam:
    def __init__(self, cx, cy, yaw=24.0, sp=.45):
        a = math.radians(yaw)
        self.cx, self.cy, self.c, self.s = cx, cy, math.cos(a), math.sin(a)
        self.sp, self.cp = sp, math.sqrt(1 - sp * sp)

    def p(self, x, y, z=0.0):
        xr = x * self.c - y * self.s
        yr = x * self.s + y * self.c
        return (self.cx + xr, self.cy + yr * self.sp - z * self.cp)

    def plane(self, x, y, z):
        """Opening tag of a group whose local circles lie flat in the plane at height z, centred on (x, y)."""
        sx, sy = self.p(x, y, z)
        return '<g transform="translate(%s %s) scale(1 %s)">' % (n(sx), n(sy), n(self.sp, 3))


def P(pts):
    return " ".join("%s,%s" % (n(x), n(y)) for x, y in pts)


def M(pts, close=False):
    return "M" + "L".join("%s %s" % (n(x), n(y)) for x, y in pts) + ("Z" if close else "")


def lerp(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


class Box:
    """A box standing on z0, turned by rot degrees on top of the camera yaw. Holds its projected faces."""

    def __init__(self, cam, x, y, hx, hy, z0, z1, rot=0.0):
        r = math.radians(rot)
        cr, sr = math.cos(r), math.sin(r)
        wc = [(x + a * cr - b * sr, y + a * sr + b * cr) for a, b in ((hx, hy), (-hx, hy), (-hx, -hy), (hx, -hy))]
        self.top = [cam.p(px, py, z1) for px, py in wc]
        self.bot = [cam.p(px, py, z0) for px, py in wc]
        self.faces = []                                  # (side, i, j): side "l" or "r", top edge i -> j
        for i in range(4):
            j = (i + 1) % 4
            mx, my = (wc[i][0] + wc[j][0]) / 2 - x, (wc[i][1] + wc[j][1]) / 2 - y
            if mx * cam.s + my * cam.c > 1e-6:
                self.faces.append(("r" if mx * cam.c - my * cam.s > 0 else "l", i, j))
        self.faces.sort()                                # left face first

    def face(self, side):
        for sd, i, j in self.faces:
            if sd == side:
                return [self.top[i], self.top[j], self.bot[j], self.bot[i]]

    def front(self):
        """Index of the corner shared by the two visible faces."""
        (_, a, b), (_, c, d) = self.faces
        return ({a, b} & {c, d}).pop()

    def top_front(self):
        """The two top edges over the visible faces, as one polyline through the front corner."""
        (_, a, b), (_, c, d) = self.faces
        f = self.front()
        ends = [k for k in (a, b, c, d) if k != f]
        return [self.top[ends[0]], self.top[f], self.top[ends[1]]]

    def apex(self):
        return min(self.top, key=lambda q: q[1])

    def bottom_edges(self):
        return "".join(M([self.bot[i], self.bot[j]]) for _, i, j in self.faces)

    def svg(self, tint=(".08", ".045", ".022"), edge=".2", top_edge=".42", fill=K, ink=W):
        """Opaque base, flat white tints per face, then the visible edges."""
        o = ['<polygon points="%s" fill="%s"/>' % (P(q), fill) for q in [self.top] + [self.face(s) for s, _, _ in self.faces]]
        o.append('<polygon points="%s" fill="%s" fill-opacity="%s"/>' % (P(self.top), ink, tint[0]))
        for s, _, _ in self.faces:
            o.append('<polygon points="%s" fill="%s" fill-opacity="%s"/>' % (P(self.face(s)), ink, tint[1] if s == "l" else tint[2]))
        verts = set()
        for _, i, j in self.faces:
            verts |= {i, j}
        o.append('<path d="%s%s" stroke="%s" stroke-opacity="%s"/>'
                 % ("".join(M([self.top[k], self.bot[k]]) for k in sorted(verts)), self.bottom_edges(), ink, edge))
        o.append('<path d="%s" stroke="%s" stroke-opacity="%s"/>' % (M(self.top, True), ink, top_edge))
        return "".join(o)

    def warm(self, bands=((0, .1, ".2"), (.1, .24, ".11"), (.24, .44, ".05")), rim=True):
        """Warm light rising up both visible faces from the bottom edge, plus a stepped rim on that edge."""
        o = []
        for s, i, j in self.faces:
            ti, tj, bi, bj = self.top[i], self.top[j], self.bot[i], self.bot[j]
            for f0, f1, op in bands:
                q = [lerp(bi, ti, f0), lerp(bj, tj, f0), lerp(bj, tj, f1), lerp(bi, ti, f1)]
                o.append('<polygon points="%s" fill="%s" fill-opacity="%s"/>' % (P(q), Y, op))
        if rim:
            o.append(glow_path(self.bottom_edges(), ((8, ".06"), (4, ".16"), (1.4, ".9"))))
        return "".join(o)


def glow_path(d, steps=((8, ".06"), (4, ".16"), (1.4, ".9")), color=Y, cls=""):
    """One path drawn several times, widest and faintest first: the flat pseudo glow."""
    return "".join('<path%s d="%s" stroke="%s" stroke-width="%s" stroke-opacity="%s"/>'
                   % (' class="%s"' % cls if cls else "", d, color, w, op) for w, op in steps)


def panel(w, h, cell=24, seams=((200, 400), (157, 313))):
    """Near-black metallic panel: fine grid, bevelled seams, rivets, stepped vignette."""
    o = ['<rect width="%d" height="%d" fill="%s"/>' % (w, h, K)]
    o.append('<path d="%s%s" stroke="%s" stroke-opacity=".03"/>'
             % ("".join("M%d 0V%d" % (x, h) for x in range(cell, w, cell)),
                "".join("M0 %dH%d" % (y, w) for y in range(cell, h, cell)), W))
    xs, ys = seams
    o.append('<path d="%s%s" stroke="#000" stroke-width="2"/>'
             % ("".join("M%d 0V%d" % (x, h) for x in xs), "".join("M0 %dH%d" % (y, w) for y in ys)))
    o.append('<path d="%s%s" stroke="%s" stroke-opacity=".07"/>'
             % ("".join("M%d 0V%d" % (x + 1.5, h) for x in xs), "".join("M0 %sH%d" % (n(y + 1.5), w) for y in ys), W))
    o.append('<path d="%s" stroke="%s" stroke-opacity=".2" stroke-width="2.6"/>'
             % ("".join("M%s %sh0" % (n(x + 7), n(y + 7)) for x in (0,) + tuple(xs) for y in (0,) + tuple(ys)), W))
    for sw, op in ((150, ".3"), (84, ".4"), (34, ".55")):
        o.append('<rect width="%d" height="%d" stroke="%s" stroke-width="%d" stroke-opacity="%s"/>' % (w, h, K, sw, op))
    return "".join(o)


def halo(x, y, steps=((200, ".012"), (150, ".016"), (104, ".022"), (64, ".03"))):
    """Warm backlight behind the subject, screen space."""
    return "".join('<circle cx="%s" cy="%s" r="%d" fill="%s" fill-opacity="%s"/>' % (n(x), n(y), r, Y, op) for r, op in steps)


def pool(cam, x, y, z, steps=((128, ".04"), (96, ".05"), (68, ".07"), (44, ".1"), (24, ".16"), (10, ".3")), cls=""):
    """Warm light pooled on a plane, stepped discs."""
    return (cam.plane(x, y, z) + ('<g class="%s">' % cls if cls else "<g>")
            + "".join('<circle r="%d" fill="%s" fill-opacity="%s"/>' % (r, Y, op) for r, op in steps) + "</g></g>")


def ring(cam, lp, x, y, z, r, turn, segs, dash, pulse_cls, dots=1, width=4.2):
    """One luminous ring lying in its plane: stepped glow (pulse class), then a turning layer with
       data segments and orbiting particles. turn: degrees per cycle (negative = counter clockwise)."""
    C = 2 * math.pi * r
    per = C / segs
    rot = lp.frames([(0, "transform:rotate(0deg)"), (lp.T, "transform:rotate(%ddeg)" % turn)], "linear")
    o = [cam.plane(x, y, z)]
    o.append('<g class="%s">' % pulse_cls)
    for sw, op in ((26, ".045"), (15, ".08"), (7, ".17")):
        o.append('<circle r="%s" stroke="%s" stroke-width="%s" stroke-opacity="%s"/>' % (n(r), Y, sw, op))
    o.append('<circle r="%s" stroke="%s" stroke-width="2.2" stroke-opacity=".7"/></g>' % (n(r), Y))
    o.append('<g class="%s"><circle r="%s"/>' % (rot, n(r + 14)))            # unpainted anchor keeps the turn centred
    o.append('<circle r="%s" stroke="%s" stroke-width="%s" stroke-dasharray="%s %s"/>'
             % (n(r), Y, width, n(per * dash), n(per * (1 - dash))))
    head = dash * 360.0 / segs if turn > 0 else 0.0
    for k in range(dots):
        a = math.radians(head + k * 360.0 / dots)
        px, py = r * math.cos(a), r * math.sin(a)
        o.append('<circle cx="%s" cy="%s" r="11" fill="%s" fill-opacity=".12"/><circle cx="%s" cy="%s" r="6.5" fill="%s" '
                 'fill-opacity=".32"/><circle cx="%s" cy="%s" r="3.6" fill="%s"/><circle cx="%s" cy="%s" r="1.5" fill="%s"/>'
                 % (n(px), n(py), Y, n(px), n(py), Y, n(px), n(py), Y, n(px), n(py), W))
    o.append('</g></g>')
    return "".join(o)


def sparkle(x, y, s=1.0, cls=""):
    """Four point glint at (x, y); the class (if any) sits on an inner group so it can pop in place."""
    q = lambda v: n(v * s)
    return ('<g transform="translate(%s %s)"><g class="%s" opacity="0"><circle r="%s" fill="%s" fill-opacity=".12"/>'
            '<circle r="%s" fill="%s" fill-opacity=".3"/><path d="M0 -%sL%s -%sL%s 0L%s %sL0 %sL-%s %sL-%s 0L-%s -%sZ" fill="%s"/>'
            '</g></g>' % (n(x), n(y), cls, q(12), Y, q(6), Y, q(15), q(2), q(2), q(15), q(2), q(2), q(15), q(2), q(2),
                          q(15), q(2), q(2), W))
