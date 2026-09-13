# -*- coding: utf-8 -*-
"""The three engine illustrations on engines.html, looping (round 8).

Same dark 3D language as the digital twin (mirror.py) and the jurisdiction stream (jurisdiction.py):
a matte black floating subject over a black platform on a near-black metallic panel, three concentric
#FFD400 rings, warm light pooled under the subject. Flat SVG only, stepped opacity glow, no gradients,
no blur, no filters. Every animated part runs on one cycle through loopkit.py (transform and opacity),
so under prefers-reduced-motion the markup itself is the composed final frame.

Engine 01, Geo Sentinel, loop 8s:
  0-8s      a matte globe floats over the site, its meridians turn 90 degrees per cycle
  0-8s      a satellite completes one inclined orbit, passing behind the globe and in front of it
  0-8s      a radar sweep crosses the site twice (one lap every 4s) inside the geofence
  on pass   each geofence post lights as the sweep reaches it; each of the three location pins
            pings (expanding ring) and sends an evidence packet up into the globe
  0.6 / 4.6s  ring glow pulses outward, inner to outer, 0.5s apart
  0-8s      the globe bobs twice (up at 2 / 6s), the light pool dims as it rises
Reduced motion: sweep parked, pins lit, rings lit, satellite shown in front of the globe.
"""
import math
import loopkit as lk
import dark3d as d3

Y, K, W = d3.Y, d3.K, d3.W
n = lk.num
VW, VH = 600, 480


# ---------------------------------------------------------------- shared helpers
def _env_at(env, dt):
    if dt < env[0][0] or dt > env[-1][0]:
        return None
    for (t0, v0), (t1, v1) in zip(env, env[1:]):
        if t0 <= dt <= t1:
            f = 0.0 if t1 == t0 else (dt - t0) / (t1 - t0)
            return tuple(a + (b - a) * f for a, b in zip(v0, v1))
    return None


def track(lp, times, env, rest, fmt):
    """Event driven keyframes that may wrap across the end of the cycle.
       env: [(dt, values)] relative to each event start; rest: values between events;
       fmt(values) -> declarations. Sampled at every breakpoint and played linear."""
    T = lp.T
    starts = [t % T for t in times]
    bps = {0.0, T}
    for s in starts:
        for sh in (-T, 0.0, T):
            for dt, _ in env:
                x = s + sh + dt
                if 0.0 <= x <= T:
                    bps.add(round(x, 4))

    def val(x):
        for s in starts:
            for sh in (-T, 0.0, T):
                v = _env_at(env, x - s - sh)
                if v is not None:
                    return v
        return rest

    return lp.frames([(x, fmt(val(x))) for x in sorted(bps)], "linear")


def _ease_out(f):
    return 1 - (1 - f) * (1 - f)


PING_ENV = ([(0.0, (0.0, 1.0)), (.04, (.9, 1.0))]
            + [(.04 + .86 * f, (.9 * (1 - _ease_out(f)), 1 + 2.4 * _ease_out(f))) for f in (.25, .5, .75, 1.0)]
            + [(.93, (0.0, 1.0))])
PING_FMT = lambda v: "opacity:%s;transform:scale(%s)" % (n(v[0], 3), n(v[1], 3))
BLIP_ENV = [(0.0, (0.0,)), (.14, (1.0,)), (.8, (0.0,))]
BLIP_FMT = lambda v: "opacity:%s" % n(v[0], 3)


def _pulse_rings(lp, cam, x, y, z, rings, pulse):
    o = []
    for i, (r, turn, segs, dash, dots) in enumerate(rings):
        pts = [(0, "opacity:.6;transform:scale(1)")]
        for t0 in pulse:
            t = t0 + .5 * i
            pts += [(t - .3, "opacity:.6;transform:scale(1)"), (t, "opacity:1;transform:scale(1.02)"),
                    (t + 1.5, "opacity:.6;transform:scale(1)")]
        o.append(d3.ring(cam, lp, x, y, z, r, turn, segs, dash, lp.frames(pts, "ease-out"), dots))
    return "".join(o)


def _bob(lp, amp, T):
    q = T / 4.0
    return lp.frames([(0, "transform:translateY(0px)"), (q, "transform:translateY(-%dpx)" % amp),
                      (2 * q, "transform:translateY(0px)"), (3 * q, "transform:translateY(-%dpx)" % amp),
                      (T, "transform:translateY(0px)")], "ease-in-out")


def _dim(lp, T):
    q = T / 4.0
    return lp.frames([(0, "opacity:1"), (q, "opacity:.7"), (2 * q, "opacity:1"), (3 * q, "opacity:.7"), (T, "opacity:1")],
                     "ease-in-out")


def _open(label):
    return ('<svg fill="none" class="lps" viewBox="0 0 %d %d" role="img" aria-label="%s" focusable="false">'
            % (VW, VH, label))


def _platform(cam, half, thick, inset=18):
    plat = d3.Box(cam, 0, 0, half, half, -thick, 0)
    o = plat.svg(tint=(".045", ".03", ".014"), edge=".16", top_edge=".26")
    ins = d3.Box(cam, 0, 0, half - inset, half - inset, 0, 0)
    return o + '<path d="%s" stroke="%s" stroke-opacity=".07"/>' % (d3.M(ins.top, True), W)


# ---------------------------------------------------------------- engine 01: Geo Sentinel
GEO_T = 8.0
G_CAM = d3.Cam(300, 322, yaw=24, sp=.45)
G_PLAT, G_PT = 172, 22
G_R, G_Z = 62, 158                     # globe radius, globe centre height
G_ZR = 36                              # ring plane
G_RINGS = [(100, 360, 4, .17, 2), (128, -360, 3, .28, 1), (156, 360, 2, .1, 2)]
G_PULSE = [.6, 4.6]
G_BOB = 7
G_SWEEP_R, G_SWEEP0, G_LAP = 150, 60.0, 4.0     # sweep radius, parked angle, seconds per lap
G_FENCE, G_FROT = 132, 12              # geofence half size and turn
G_PINS = [(118, 100), (150, 205), (140, 330)]   # plane polar (radius, angle): front, left, right back
G_ORBIT = (114, 35.0, -30.0, 200.0)    # radius, node angle, inclination, start angle (degrees)
G_MERIDIANS, G_SPIN, G_KF = 4, 90.0, 18


def _hit_times(alpha):
    """Seconds into the cycle at which the sweep passes plane angle alpha (two laps per cycle)."""
    t = ((alpha - G_SWEEP0) % 360.0) / 360.0 * G_LAP
    return [t, t + G_LAP]


def _plane_angle(cam, x, y):
    cx, cy = cam.p(0, 0, 0)
    px, py = cam.p(x, y, 0)
    return math.degrees(math.atan2((py - cy) / cam.sp, px - cx)) % 360.0


def _svd(p, q, r, s):
    """A = [[p, q], [r, s]] = R(beta) diag(sx, sy) R(gamma), sy signed."""
    E, F, G, H = (p + s) / 2, (p - s) / 2, (r + q) / 2, (r - q) / 2
    Q, Rr = math.hypot(E, H), math.hypot(F, G)
    a1, a2 = math.atan2(G, F), math.atan2(H, E)
    return (a2 + a1) / 2, Q + Rr, Q - Rr, (a2 - a1) / 2


def _meridian(lp, phi0, sp, cp):
    """Front half of a turning meridian: a fixed semicircle under rotate() scale() rotate(),
       sampled every G_SPIN / G_KF degrees and unwrapped so every function interpolates smoothly."""
    pts, prev = [], None
    for k in range(G_KF + 1):
        phi = math.radians(phi0 + G_SPIN * k / G_KF)
        beta, sx, sy, gamma = _svd(math.cos(phi), 0.0, math.sin(phi) * sp, -cp)
        psi = math.atan2(sp, math.sin(phi) * cp)          # centre of the visible half, in great circle angle
        g = gamma + psi - math.pi / 2
        if prev is not None:
            best = None
            for m in range(-4, 5):
                for j in range(-4, 5):
                    if (m + j) % 2:
                        continue
                    b2, g2 = beta + m * math.pi, g + j * math.pi
                    cost = abs(b2 - prev[0]) + abs(g2 - prev[1])
                    if best is None or cost < best[0]:
                        best = (cost, b2, g2)
            beta, g = best[1], best[2]
        prev = (beta, g)
        pts.append((GEO_T * k / G_KF, "transform:rotate(%sdeg) scale(%s,%s) rotate(%sdeg)"
                    % (n(math.degrees(beta), 2), n(sx, 4), n(sy, 4), n(math.degrees(g), 2))))
    return lp.frames(pts, "linear")


def _lat_runs(R, lat, sp, cp):
    zc, rc = math.sin(math.radians(lat)), math.cos(math.radians(lat))
    runs, cur = [], []
    for k in range(-90, 271, 5):
        th = math.radians(k)
        if rc * math.sin(th) * cp + zc * sp > 0:
            cur.append((R * rc * math.cos(th), R * (rc * math.sin(th) * sp - zc * cp)))
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


def _orbit_point(u_deg, sp, cp):
    ro, a, inc, _ = G_ORBIT
    a, inc, u = math.radians(a), math.radians(inc), math.radians(u_deg)
    e1 = (math.cos(a), math.sin(a), 0.0)
    e2 = (-math.sin(a) * math.cos(inc), math.cos(a) * math.cos(inc), math.sin(inc))
    x, y, z = [ro * (math.cos(u) * e1[i] + math.sin(u) * e2[i]) for i in range(3)]
    return x, y * sp - z * cp, y * cp + z * sp          # screen dx, screen dy, depth toward the viewer


def _satellite(x, y):
    """Satellite in screen space at (x, y): matte body, two panels, a warm beacon."""
    return ('<g transform="translate(%s %s) rotate(-18)">'
            '<path d="M-26 -5H-9V5H-26ZM9 -5H26V5H9Z" fill="%s"/>'
            '<path d="M-26 -5H-9V5H-26ZM9 -5H26V5H9Z" fill="%s" fill-opacity=".1" stroke="%s" stroke-opacity=".5"/>'
            '<path d="M-20.3 -5V5M-14.7 -5V5M14.7 -5V5M20.3 -5V5M-26 0H-9M9 0H26" stroke="%s" stroke-opacity=".22"/>'
            '<path d="M-9 0H-6M6 0H9" stroke="%s" stroke-opacity=".5"/>'
            '<rect x="-6" y="-7" width="12" height="14" fill="%s"/>'
            '<rect x="-6" y="-7" width="12" height="14" fill="%s" fill-opacity=".12" stroke="%s" stroke-opacity=".55"/>'
            '<path d="M0 -7V-12" stroke="%s" stroke-opacity=".6"/>'
            '<circle cy="-13" r="7" fill="%s" fill-opacity=".12"/><circle cy="-13" r="4" fill="%s" fill-opacity=".32"/>'
            '<circle cy="-13" r="2" fill="%s"/></g>' % (n(x), n(y), K, W, W, W, W, K, W, W, W, Y, Y, Y))


def _globe(lp, R, sp, cp):
    """Matte globe centred on (0, 0): stepped shading, warm underside, latitudes and turning meridians."""
    o = ['<circle r="%d" fill="%s"/>' % (R, K)]
    for cx, cy, rr, op in ((-.13, -.15, .78, ".035"), (-.25, -.3, .6, ".04"), (-.36, -.4, .36, ".045")):
        o.append('<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="%s"/>' % (n(cx * R), n(cy * R), n(rr * R), W, op))
    for ry, op in ((.12, ".03"), (.46, ".05"), (.72, ".09"), (.88, ".16")):
        o.append('<path d="M-%d 0A%d %d 0 0 0 %d 0A%d %s 0 0 1 -%d 0Z" fill="%s" fill-opacity="%s"/>'
                 % (R, R, R, R, R, n(ry * R), R, Y, op))
    for lat in (-38, 22, 48):
        o.append('<path d="%s" stroke="%s" stroke-opacity=".17"/>' % ("".join(d3.M(rn) for rn in _lat_runs(R, lat, sp, cp)), W))
    o.append(d3.glow_path("".join(d3.M(rn) for rn in _lat_runs(R, -8, sp, cp)), ((4, ".06"), (2, ".16"), (1, ".6"))))
    base = "M%d 0A%d %d 0 0 1 -%d 0" % (R, R, R, R)
    for i in range(G_MERIDIANS):
        cls = _meridian(lp, i * 180.0 / G_MERIDIANS, sp, cp)
        o.append('<g class="%s"><circle r="%d"/><path d="%s" stroke="%s" stroke-opacity=".2" '
                 'vector-effect="non-scaling-stroke"/></g>' % (cls, R, base, W))
    o.append('<circle r="%d" stroke="%s" stroke-opacity=".2"/>' % (R, W))
    a0, a1 = math.radians(196), math.radians(262)
    o.append('<path d="M%s %sA%d %d 0 0 1 %s %s" stroke="%s" stroke-opacity=".38" stroke-width="1.6"/>'
             % (n(R * math.cos(a0)), n(R * math.sin(a0)), R, R, n(R * math.cos(a1)), n(R * math.sin(a1)), W))
    b0, b1 = math.radians(22), math.radians(158)
    o.append(d3.glow_path("M%s %sA%d %d 0 0 1 %s %s" % (n(R * math.cos(b0)), n(R * math.sin(b0)), R, R,
                                                          n(R * math.cos(b1)), n(R * math.sin(b1))),
                          ((7, ".06"), (3.5, ".16"), (1.4, ".85"))))
    return "".join(o)


def geo_svg():
    lp = lk.Loop("eg", GEO_T, "engines: geo sentinel globe, orbit and sweep, dark 3D, loop %gs" % GEO_T)
    cam = G_CAM
    sp, cp = cam.sp, cam.cp
    o = [_open("Geo Sentinel: a globe with an orbiting satellite, a radar sweep and location pings over a monitored site")]
    o.append(d3.panel(VW, VH, seams=((200, 400), (160, 320))))
    gx, gy = cam.p(0, 0, G_Z)
    o.append(d3.halo(gx, gy + 24))
    o.append(_platform(cam, G_PLAT, G_PT))
    dim = _dim(lp, GEO_T)
    o.append(d3.pool(cam, 0, 0, 0, cls=dim))

    # geofence: dashed perimeter with four posts that light as the sweep passes them
    fence = d3.Box(cam, 0, 0, G_FENCE, G_FENCE, 0, 0, G_FROT).top
    o.append('<polygon points="%s" fill="%s" fill-opacity=".025"/>' % (d3.P(fence), Y))
    o.append('<path d="%s" stroke="%s" stroke-opacity=".38" stroke-dasharray="7 7"/>' % (d3.M(fence, True), Y))

    # radar sweep lying on the site, two laps per cycle, parked at G_SWEEP0 in the static frame
    rot = lp.frames([(0, "transform:rotate(0deg)"), (GEO_T, "transform:rotate(%ddeg)" % (360 * GEO_T / G_LAP))], "linear")
    cx0, cy0 = cam.p(0, 0, 0)
    RS = G_SWEEP_R
    o.append('<g transform="translate(%s %s) scale(1 %s)"><circle r="%d" stroke="%s" stroke-opacity=".1"/>'
             '<circle r="%d" stroke="%s" stroke-opacity=".07" stroke-dasharray="2 8"/><g transform="rotate(%s)">'
             % (n(cx0), n(cy0), n(sp, 3), RS, Y, RS * 2 // 3, W, n(G_SWEEP0)))
    o.append('<g class="%s"><circle r="%d"/>' % (rot, RS + 2))
    for w, op in ((46, ".04"), (26, ".06"), (11, ".1")):
        a = math.radians(-w)
        o.append('<path d="M0 0L%s %sA%d %d 0 0 1 %d 0Z" fill="%s" fill-opacity="%s"/>'
                 % (n(RS * math.cos(a)), n(RS * math.sin(a)), RS, RS, RS, Y, op))
    o.append(d3.glow_path("M0 0H%d" % RS, ((6, ".08"), (3, ".2"), (1.3, ".9"))))
    o.append('</g></g></g>')

    corners = []
    r_ = math.radians(G_FROT)
    for a, b in ((G_FENCE, G_FENCE), (-G_FENCE, G_FENCE), (-G_FENCE, -G_FENCE), (G_FENCE, -G_FENCE)):
        corners.append((a * math.cos(r_) - b * math.sin(r_), a * math.sin(r_) + b * math.cos(r_)))
    corners.sort(key=lambda c: cam.p(c[0], c[1], 0)[1])            # back to front
    for wx, wy in corners:
        post = d3.Box(cam, wx, wy, 3.5, 3.5, 0, 18, G_FROT)
        o.append(post.svg(tint=(".16", ".08", ".04"), edge=".3", top_edge=".5"))
        tx, ty = cam.p(wx, wy, 22)
        blip = track(lp, _hit_times(_plane_angle(cam, wx, wy)), BLIP_ENV, (0.0,), BLIP_FMT)
        o.append('<circle cx="%s" cy="%s" r="2.4" fill="%s" fill-opacity=".7"/>' % (n(tx), n(ty), Y))
        o.append('<g class="%s" opacity="0"><circle cx="%s" cy="%s" r="10" fill="%s" fill-opacity=".14"/>'
                 '<circle cx="%s" cy="%s" r="5" fill="%s" fill-opacity=".4"/><circle cx="%s" cy="%s" r="2.2" fill="%s"/></g>'
                 % (blip, n(tx), n(ty), Y, n(tx), n(ty), Y, n(tx), n(ty), W))

    # location pins: ground ring, stem, lit head; each pings and uplinks when the sweep reaches it
    target = (gx, gy + G_R - 8)
    uplinks = []
    for r, al in sorted(G_PINS, key=lambda pa: math.sin(math.radians(pa[1]))):
        a = math.radians(al)
        bx, by = cx0 + r * math.cos(a), cy0 + r * math.sin(a) * sp
        hx, hy = bx, by - 24
        hits = _hit_times(al)
        o.append('<g transform="translate(%s %s) scale(1 %s)"><circle r="8" stroke="%s" stroke-opacity=".55"/>'
                 '<circle class="%s" r="9" stroke="%s" stroke-width="1.6" vector-effect="non-scaling-stroke" opacity="0"/></g>'
                 % (n(bx), n(by), n(sp, 3), Y, track(lp, hits, PING_ENV, (0.0, 1.0), PING_FMT), Y))
        o.append('<path d="M%s %sV%s" stroke="%s" stroke-opacity=".45"/>' % (n(bx), n(by), n(hy + 3), W))
        o.append('<path d="M%s %sL%s %s" stroke="%s" stroke-opacity=".12" stroke-dasharray="2 6"/>'
                 % (n(hx), n(hy), n(target[0]), n(target[1]), Y))
        o.append('<circle cx="%s" cy="%s" r="9" fill="%s" fill-opacity=".12"/><circle cx="%s" cy="%s" r="5" fill="%s" '
                 'fill-opacity=".32"/><circle cx="%s" cy="%s" r="3" fill="%s"/><circle cx="%s" cy="%s" r="1.2" fill="%s"/>'
                 % (n(hx), n(hy), Y, n(hx), n(hy), Y, n(hx), n(hy), Y, n(hx), n(hy), W))
        o.append('<g class="%s" opacity="0"><circle cx="%s" cy="%s" r="16" fill="%s" fill-opacity=".1"/>'
                 '<circle cx="%s" cy="%s" r="9" fill="%s" fill-opacity=".22"/></g>'
                 % (track(lp, hits, BLIP_ENV, (0.0,), BLIP_FMT), n(hx), n(hy), Y, n(hx), n(hy), Y))
        uplinks.append((hx, hy, [t + .25 for t in hits]))

    # the three rings under the globe
    o.append(_pulse_rings(lp, cam, 0, 0, G_ZR, G_RINGS, G_PULSE))

    # evidence packets riding the uplinks into the globe
    arrivals = []
    for hx, hy, starts in uplinks:
        dur = 1.3
        o.append('<g class="%s" opacity="0"><circle cx="%s" cy="%s" r="6" fill="%s" fill-opacity=".22"/>'
                 '<rect x="%s" y="%s" width="4" height="4" fill="%s"/></g>'
                 % (lp.moves([(t, dur) for t in starts], target[0] - hx, target[1] - hy, .2),
                    n(hx), n(hy), Y, n(hx - 2), n(hy - 2), Y))
        arrivals += [t + dur for t in starts]

    # globe, orbit and satellite, bobbing together
    o.append('<g class="%s">' % _bob(lp, G_BOB, GEO_T))
    ro, _, _, u0 = G_ORBIT
    ring_pts = [_orbit_point(u0 + k * 5.0, sp, cp) for k in range(73)]
    back = [(gx + dx, gy + dy) if dp < 0 else None for dx, dy, dp in ring_pts]
    front = [(gx + dx, gy + dy) if dp >= 0 else None for dx, dy, dp in ring_pts]

    def runs(seq):
        out, cur = [], []
        for q in seq:
            if q is None:
                if len(cur) > 1:
                    out.append(cur)
                cur = []
            else:
                cur.append(q)
        if len(cur) > 1:
            out.append(cur)
        return "".join(d3.M(r) for r in out)

    o.append('<path d="%s" stroke="%s" stroke-opacity=".16" stroke-dasharray="3 6"/>' % (runs(back), W))
    sx0, sy0, _ = ring_pts[0]
    steps = 48
    fr_front, fr_back = [], []
    for k in range(steps + 1):
        dx, dy, dp = _orbit_point(u0 + 360.0 * k / steps, sp, cp)
        tr = "transform:translate(%spx,%spx)" % (n(dx - sx0), n(dy - sy0))
        t = GEO_T * k / steps
        fr_front.append((t, "opacity:%s;%s" % ("1" if dp >= 0 else "0", tr)))
        fr_back.append((t, "opacity:%s;%s" % ("0" if dp >= 0 else ".75", tr)))
    first_front = ring_pts[0][2] >= 0
    o.append('<g class="%s"%s>%s</g>' % (lp.frames(fr_back, "linear"), ' opacity="0"' if first_front else "",
                                         _satellite(gx + sx0, gy + sy0)))
    flash = track(lp, arrivals, [(0.0, (0.0,)), (.12, (1.0,)), (.7, (0.0,))], (0.0,), BLIP_FMT)
    o.append('<g transform="translate(%s %s)">%s' % (n(gx), n(gy), _globe(lp, G_R, sp, cp)))
    b0, b1 = math.radians(30), math.radians(150)
    o.append('<g class="%s" opacity="0">%s</g></g>'
             % (flash, d3.glow_path("M%s %sA%d %d 0 0 1 %s %s" % (n(G_R * math.cos(b0)), n(G_R * math.sin(b0)), G_R, G_R,
                                                                   n(G_R * math.cos(b1)), n(G_R * math.sin(b1))),
                                    ((12, ".1"), (6, ".22"), (2.4, "1")))))
    o.append('<path d="%s" stroke="%s" stroke-opacity=".34" stroke-dasharray="3 6"/>' % (runs(front), W))
    o.append('<g class="%s"%s>%s</g>' % (lp.frames(fr_front, "linear"), "" if first_front else ' opacity="0"',
                                         _satellite(gx + sx0, gy + sy0)))
    o.append('</g></svg>')
    return "".join(o)


# ---------------------------------------------------------------- page hooks
BUILDERS = {"geo": (geo_svg, GEO_T)}


def figure(key):
    """Figure for an engine key from build.ENGINES, or None if that engine still uses its static image."""
    b = BUILDERS.get(key)
    if not b:
        return None
    return '<figure class="lpan" data-loop data-engine="%s">%s</figure>' % (key, b[0]())


if __name__ == "__main__":
    for k, (fn, T) in BUILDERS.items():
        print("engine %-6s svg %.2f KB, loop %gs" % (k, len(fn().encode()) / 1024.0, T))
