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

Engine 02, Aura Verification Engine, loop 8s: four source lanes feed a floating AI chip, a drifting record
is flagged and rejected at the outer ring, coherence is confirmed twice per cycle (see aura_svg).

Engine 03, Pedigree Engine, loop 8s: a custody chain hands evidence into the core, a sealed block drops and
locks onto a floating ledger stack, the lineage check runs down the stack, the trust score dial updates,
then the stack settles one pitch so the cycle closes seamlessly (see pedigree_svg).
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


# ---------------------------------------------------------------- engine 02: Aura Verification Engine
AURA_T = 8.0
A_CAM = d3.Cam(300, 318, yaw=24, sp=.45)
A_PLAT, A_PT = 184, 22
A_ZR = 36
A_RINGS = [(100, 360, 4, .17, 2), (128, -360, 3, .28, 1), (156, 360, 2, .1, 2)]
A_PULSE = [.6, 4.6]
A_BOB = 7
A_ROT = 16
A_SLAB, A_SZ = 74, (106, 126)          # chip base half size and z range
A_DIE, A_DZ = 42, (126, 140)           # raised die half size and z range
A_TILES = [(12, "doc"), (150, "target"), (208, "bars"), (322, "node")]   # plane angle, mark
A_PHASE = [.0, .25, .5, .75]           # one packet per lane, two rides per cycle: a landing every second
A_LANE_IN = 60                         # lanes end under the chip
A_VERIFY = [2.4, 6.4]                  # coherence confirmed: wave, full grid, badge, sparkle
A_ANOM = (3.1, 4.3, 5.0, 5.7)          # drift packet: enters, stops at the ring, flagged, rejected
A_ANOM_LANE = 1


def _local_to_world(cam, r, al):
    """Plane polar (screen aligned) to world plan coordinates."""
    xr, yr = r * math.cos(math.radians(al)), r * math.sin(math.radians(al))
    return xr * cam.c + yr * cam.s, -xr * cam.s + yr * cam.c


def _plane_xy(cam, r, al, z=0.0):
    cx, cy = cam.p(0, 0, z)
    return cx + r * math.cos(math.radians(al)), cy + r * math.sin(math.radians(al)) * cam.sp


def _tile_mark(kind):
    """Flat source glyph lying on a tile top (drawn inside a plane group)."""
    if kind == "doc":
        return ('<path d="M-6 -8H3L7 -4V8H-6Z" stroke="%s" stroke-width="1.4"/><path d="M-3 -2H4M-3 1.5H4M-3 5H1" stroke="%s"/>'
                % (Y, Y))
    if kind == "target":
        return ('<circle r="7" stroke="%s" stroke-width="1.4"/><circle r="2.2" fill="%s"/><path d="M-10 0H-7M7 0H10M0 -10V-7M0 7V10" '
                'stroke="%s"/>' % (Y, Y, Y))
    if kind == "bars":
        return '<path d="M-7 6V1H-3.5V6ZM-1.75 6V-3H1.75V6ZM3.5 6V-7H7V6Z" fill="%s"/>' % Y
    return ('<path d="M0 -8L7 -4V4L0 8L-7 4V-4Z" stroke="%s" stroke-width="1.4"/><circle r="2.4" fill="%s"/>' % (Y, Y))


def aura_svg():
    lp = lk.Loop("ea", AURA_T, "engines: aura verification chip, lanes and drift rejection, dark 3D, loop %gs" % AURA_T)
    cam = A_CAM
    sp = cam.sp
    o = [_open("Aura Verification Engine: evidence from four sources is checked by an AI core, a drifting record is "
               "flagged and rejected, coherent records are confirmed")]
    o.append(d3.panel(VW, VH, seams=((200, 400), (160, 320))))
    hx, hy = cam.p(0, 0, A_SZ[1])
    o.append(d3.halo(hx, hy + 30))
    o.append(_platform(cam, A_PLAT, A_PT))
    dim = _dim(lp, AURA_T)
    o.append(d3.pool(cam, 0, 0, 0, cls=dim))

    # four source tiles, each with a lane into the core; one packet per lane, two rides per cycle
    tiles = []
    for al, kind in A_TILES:
        r = 200.0
        while True:
            wx, wy = _local_to_world(cam, r, al)
            if max(abs(wx), abs(wy)) <= A_PLAT - 26:
                break
            r -= 2
        tiles.append((al, kind, r, wx, wy))
    for al, kind, r, wx, wy in tiles:
        x0, y0 = _plane_xy(cam, r - 24, al)
        x1, y1 = _plane_xy(cam, A_LANE_IN, al)
        o.append(d3.glow_path("M%s %sL%s %s" % (n(x0), n(y0), n(x1), n(y1)), ((5, ".03"), (2.2, ".08"), (1, ".32"))))
        for f in (.3, .52, .74):
            cx, cy = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            o.append('<circle cx="%s" cy="%s" r="1.6" fill="%s" fill-opacity=".45"/>' % (n(cx), n(cy), Y))
    landings, emits = [], []
    for k, (al, kind, r, wx, wy) in enumerate(tiles):
        x0, y0 = _plane_xy(cam, r - 24, al)
        x1, y1 = _plane_xy(cam, A_LANE_IN, al)
        ph = A_PHASE[k]
        cls, arr = d3.stream(lp, ph, x1 - x0, y1 - y0, laps=2, edge=.12)
        landings += arr
        emits.append([(t - AURA_T / 2.0) % AURA_T for t in arr] or [0.0])
        px, py = x0 + (x1 - x0) * ph, y0 + (y1 - y0) * ph
        o.append('<g class="%s"><circle cx="%s" cy="%s" r="8" fill="%s" fill-opacity=".14"/><circle cx="%s" cy="%s" r="4.5" '
                 'fill="%s" fill-opacity=".35"/><rect x="%s" y="%s" width="4.4" height="4.4" fill="%s"/></g>'
                 % (cls, n(px), n(py), Y, n(px), n(py), Y, n(px - 2.2), n(py - 2.2), Y))
    landings.sort()

    # drift packet: white, rides the left lane, stops at the outer ring, is flagged, then rejected outward
    al, kind, r, wx, wy = tiles[A_ANOM_LANE]
    ax0, ay0 = _plane_xy(cam, r - 24, al)
    stop = _plane_xy(cam, 158, al)
    back = _plane_xy(cam, r + 6, al)
    t0, t1, t2, t3 = A_ANOM
    mv = lambda p, op: "opacity:%s;transform:translate(%spx,%spx)" % (op, n(p[0] - ax0), n(p[1] - ay0))
    drift = lp.frames([(0, mv((ax0, ay0), 0)), (t0, mv((ax0, ay0), 0)), (t0 + .2, mv((ax0, ay0), 1)),
                       (t1, mv(stop, 1)), (t2, mv(stop, 1)), (t3, mv(back, 0)), (t3 + .03, mv((ax0, ay0), 0))], "ease-in-out")
    o.append('<g class="%s" opacity="0"><circle cx="%s" cy="%s" r="8" fill="%s" fill-opacity=".12"/>'
             '<rect x="%s" y="%s" width="7" height="7" stroke="%s" stroke-width="1.4"/></g>'
             % (drift, n(ax0), n(ay0), W, n(ax0 - 3.5), n(ay0 - 3.5), W))

    for al, kind, r, wx, wy in sorted(tiles, key=lambda t: cam.p(t[3], t[4], 0)[1]):
        tile = d3.Box(cam, wx, wy, 17, 17, 0, 24, A_ROT)
        o.append(tile.svg(tint=(".1", ".06", ".03"), edge=".26", top_edge=".46"))
        o.append(tile.warm(bands=((0, .18, ".14"), (.18, .4, ".06")), rim=False))
        tx, ty = cam.p(wx, wy, 24)
        o.append('<g transform="translate(%s %s) scale(1 %s)">%s</g>' % (n(tx), n(ty), n(sp, 3), _tile_mark(kind)))
    for k, (al, kind, r, wx, wy) in enumerate(tiles):
        tx, ty = cam.p(wx, wy, 24)
        o.append('<g class="%s" opacity="0"><circle cx="%s" cy="%s" r="22" fill="%s" fill-opacity=".08"/>'
                 '<circle cx="%s" cy="%s" r="12" fill="%s" fill-opacity=".16"/></g>'
                 % (track(lp, emits[k], BLIP_ENV, (0.0,), BLIP_FMT), n(tx), n(ty), Y, n(tx), n(ty), Y))

    # rings, then the processing wave that confirms coherence
    o.append(_pulse_rings(lp, cam, 0, 0, A_ZR, A_RINGS, A_PULSE))
    o.append(cam.plane(0, 0, A_ZR) + '<circle class="%s" r="56" stroke="%s" stroke-width="1.6" vector-effect="non-scaling-stroke" '
             'opacity="0"/></g>' % (lp.rings(A_VERIFY, 1.5, 3.1, .8), Y))

    # drift flag above the stopped packet: white ring and warning mark
    fx, fy = stop
    o.append('<g transform="translate(%s %s) scale(1 %s)"><circle class="%s" r="10" stroke="%s" stroke-width="1.5" '
             'vector-effect="non-scaling-stroke" opacity="0"/></g>'
             % (n(fx), n(fy), n(sp, 3), lp.rings([t1 + .05, t1 + .4], .6, 2.6, .9), W))
    flag = track(lp, [t1 + .05], [(0.0, (0.0, 0.0)), (.25, (1.0, 1.0)), (t3 - t1 - .45, (1.0, 1.0)), (t3 - t1 - .1, (0.0, .6))],
                 (0.0, 0.0), PING_FMT)
    o.append('<g transform="translate(%s %s)"><g class="%s" opacity="0"><path d="M0 -14L12 7H-12Z" fill="%s" stroke="%s" '
             'stroke-width="1.6"/><path d="M0 -6V1M0 3.6V4" stroke="%s" stroke-width="2"/></g></g>'
             % (n(fx), n(fy - 26), flag, K, W, W))

    # the AI core: a floating chip, raised die with a 3x3 cell grid lit by each landing
    o.append('<g class="%s">' % _bob(lp, A_BOB, AURA_T))
    slab = d3.Box(cam, 0, 0, A_SLAB, A_SLAB, A_SZ[0], A_SZ[1], A_ROT)
    o.append(slab.svg(tint=(".085", ".05", ".024"), edge=".22", top_edge=".4"))
    o.append(slab.warm(bands=((0, .22, ".2"), (.22, .5, ".08"))))
    o.append('<g class="%s" opacity="0">%s</g>'
             % (track(lp, landings, [(0.0, (0.0,)), (.1, (1.0,)), (.6, (0.0,))], (0.0,), BLIP_FMT),
                d3.glow_path(slab.bottom_edges(), ((10, ".1"), (5, ".24"), (2, "1")))))
    rr = math.radians(A_ROT)
    pins = []
    for k in range(-3, 4):
        u = k * 18.0
        for a, b in ((u, A_SLAB - 10), (A_SLAB - 10, u)):
            q0 = (a * math.cos(rr) - b * math.sin(rr), a * math.sin(rr) + b * math.cos(rr))
            pins.append(cam.p(q0[0], q0[1], A_SZ[1]))
    o.append('<path d="%s" stroke="%s" stroke-opacity=".5" stroke-width="2"/>' % ("".join("M%s %sh0" % (n(x), n(y)) for x, y in pins), Y))
    die = d3.Box(cam, 0, 0, A_DIE, A_DIE, A_DZ[0], A_DZ[1], A_ROT)
    o.append(die.svg(tint=(".1", ".06", ".03"), edge=".26", top_edge=".55"))
    cells = []
    for i in range(3):
        for j in range(3):
            u, v = (i - 1) * 24.0, (j - 1) * 24.0
            cxw, cyw = u * math.cos(rr) - v * math.sin(rr), u * math.sin(rr) + v * math.cos(rr)
            cells.append(d3.Box(cam, cxw, cyw, 9, 9, A_DZ[1], A_DZ[1], A_ROT).top)
    o.append('<path d="%s" fill="%s" fill-opacity=".1" stroke="%s" stroke-opacity=".3"/>' % ("".join(d3.M(c, True) for c in cells), Y, Y))
    order = [4, 0, 8, 2, 6, 1, 7, 3, 5]
    for idx, c in enumerate(cells):
        mine = [t for m, t in enumerate(landings) if order[m % 9] == idx]
        mine += [t + .08 * idx for t in A_VERIFY]
        o.append('<polygon class="%s" opacity="0" points="%s" fill="%s"/>'
                 % (track(lp, mine, [(0.0, (0.0,)), (.08, (.95,)), (.55, (0.0,))], (0.0,), BLIP_FMT), d3.P(c), Y))
    ax, ay = die.apex()
    sp_pts = [(0, "opacity:0;transform:scale(0) rotate(0deg)")]
    for t in A_VERIFY:
        sp_pts += [(t + .7, "opacity:0;transform:scale(0) rotate(0deg)"), (t + .95, "opacity:1;transform:scale(1) rotate(45deg)"),
                   (t + 1.5, "opacity:0;transform:scale(.3) rotate(90deg)"), (t + 1.53, "opacity:0;transform:scale(0) rotate(0deg)")]
    o.append(d3.sparkle(ax, ay, .9, lp.frames(sp_pts, "ease-out")))
    badge = track(lp, [t + .3 for t in A_VERIFY], [(0.0, (0.0, 0.0)), (.3, (1.0, 1.0)), (1.25, (1.0, 1.0)), (1.6, (0.0, 1.0))],
                  (0.0, 0.0), PING_FMT)
    bx, by = ax + 62, ay - 12
    o.append('<g transform="translate(%s %s)"><g class="%s"><circle r="22" fill="%s" fill-opacity=".08"/>'
             '<circle r="15" fill="%s"/><path d="M-6 .5L-1.8 4.6L6.4 -4" stroke="%s" stroke-width="2.4"/></g></g>'
             % (n(bx), n(by), badge, Y, Y, K))
    o.append('</g></svg>')
    return "".join(o)


# ---------------------------------------------------------------- engine 03: Pedigree Engine
# Loop 8s:
#   0.15-2.05s  an evidence packet is handed along a four node custody chain, each node lights on hand-off,
#               then the packet enters the core and a beam rises into the ledger
#   1.95-2.4s   a sealed block appears above the stack and drops onto it; lock flash, ring pulse, padlock pops
#   2.75-3.65s  the lineage check runs down the stack, newest block to origin block
#   3.75-4.05s  the result rides to the trust score dial, whose head tick flashes (score recomputed)
#   6.3-7.6s    the stack settles one pitch down and the origin block is archived into the core, so the
#               last frame equals the first
# Reduced motion: four locked blocks, padlock shown, dial lit.
PED_T = 8.0
P_CAM = d3.Cam(300, 326, yaw=24, sp=.45)
P_PLAT, P_PT = 176, 22
P_ZR = 36
P_RINGS = [(100, 360, 4, .17, 2), (128, -360, 3, .28, 1), (156, 360, 2, .1, 2)]
P_PULSE = [2.4, 5.5]
P_BOB = 6
P_ROT = 16
P_BLK, P_BH, P_GAP, P_Z0 = 56, 15, 8, 104      # ledger block half size, height, gap, lowest block base
P_PITCH = P_BH + P_GAP
P_NODES = [(292, "key"), (218, "seal"), (146, "doc"), (72, "hand")]   # plane angle, mark: first hand-off to last
P_HOPS = [(.15, .55), (.7, 1.1), (1.25, 1.65), (1.75, 2.05)]         # packet rides: node to node, then into the core
P_DROP, P_LOCK = 1.95, 2.4
P_TRACE = [2.75, 3.05, 3.35, 3.65]             # lineage flash per slot, top slot first
P_SCORE = (3.75, 4.05)
P_SHIFT = (6.3, 7.6)
P_TICKS, P_LIT = 18, 14


def _custody_mark(kind):
    if kind == "key":
        return ('<circle cx="-3" r="4.5" stroke="%s" stroke-width="1.4"/><path d="M1.5 0H9M6 0V3.5M8.5 0V2.5" stroke="%s" '
                'stroke-width="1.4"/>' % (Y, Y))
    if kind == "seal":
        return ('<circle r="7.5" stroke="%s" stroke-width="1.4"/><path d="M-3.5 .2L-1 2.8L3.8 -2.4" stroke="%s" stroke-width="1.6"/>'
                % (Y, Y))
    if kind == "doc":
        return _tile_mark("doc")
    return ('<path d="M-8 -2H4L1 -5M8 2H-4L-1 5" stroke="%s" stroke-width="1.4"/>' % Y)


def _chain_links(a, b):
    """Two interlocked links at the middle of a custody hop, aligned with it."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    return ('<g transform="translate(%s %s) rotate(%s)"><rect x="-10" y="-3.5" width="12" height="7" rx="3.5" fill="%s" '
            'stroke="%s" stroke-opacity=".6" stroke-width="1.4"/><rect x="-2" y="-3.5" width="12" height="7" rx="3.5" '
            'stroke="%s" stroke-width="1.4"/></g>' % (n(mx), n(my), n(ang, 1), K, Y, Y))


def _ledger_block(cam, z0):
    """One matte ledger block: warm seam, record lines on the left face, hash ticks on the right, hash mark on top."""
    b = d3.Box(cam, 0, 0, P_BLK, P_BLK, z0, z0 + P_BH, P_ROT)
    o = [b.svg(tint=(".09", ".055", ".026"), edge=".24", top_edge=".46")]
    o.append(b.warm(bands=((0, .3, ".12"),), rim=False))
    o.append('<path d="%s" stroke="%s" stroke-opacity=".55"/>' % (b.bottom_edges(), Y))
    for s, i, j in b.faces:
        ti, tj, bi, bj = b.top[i], b.top[j], b.bot[i], b.bot[j]
        mid = lambda f: d3.lerp(d3.lerp(ti, bi, .5), d3.lerp(tj, bj, .5), f)
        if s == "l":
            o.append('<path d="%s" stroke="%s" stroke-opacity=".3"/>'
                     % ("".join(d3.M([mid(f0), mid(f1)]) for f0, f1 in ((.1, .38), (.46, .6), (.68, .9))), W))
        else:
            o.append('<path d="%s" stroke="%s" stroke-opacity=".6" stroke-width="2"/>'
                     % ("".join("M%s %sh0" % (n(mid(f)[0]), n(mid(f)[1])) for f in (.14, .26, .38, .5, .62, .74, .86)), Y))
    tx, ty = cam.p(0, 0, z0 + P_BH)
    o.append('<g transform="translate(%s %s) scale(1 %s)"><path d="M0 -17L14.7 -8.5V8.5L0 17L-14.7 8.5V-8.5Z" stroke="%s" '
             'stroke-opacity=".55" stroke-width="1.4"/><circle r="4" fill="%s" fill-opacity=".7"/></g>'
             % (n(tx), n(ty), n(cam.sp, 3), Y, Y))
    return b, "".join(o)


def pedigree_svg():
    lp = lk.Loop("ep", PED_T, "engines: pedigree ledger stack, custody chain and trust score, dark 3D, loop %gs" % PED_T)
    cam = P_CAM
    sp, cp = cam.sp, cam.cp
    o = [_open("Pedigree Engine: evidence is handed along a custody chain, sealed into a new ledger block that locks "
               "onto the verified history, the lineage is checked end to end and the trust score is updated")]
    o.append(d3.panel(VW, VH, seams=((200, 400), (160, 320))))
    top_z = P_Z0 + 3 * P_PITCH + P_BH
    hx, hy = cam.p(0, 0, top_z)
    o.append(d3.halo(hx, hy + 40))
    o.append(_platform(cam, P_PLAT, P_PT))
    o.append(d3.pool(cam, 0, 0, 0, cls=_dim(lp, PED_T)))

    # custody chain: four hand-off nodes on the platform, joined by a dashed chain that ends in the core
    nodes = []
    for al, kind in P_NODES:
        r = 200.0
        while True:
            wx, wy = _local_to_world(cam, r, al)
            if max(abs(wx), abs(wy)) <= P_PLAT - 26:
                break
            r -= 2
        nodes.append((al, kind, wx, wy, cam.p(wx, wy, 0)))
    core = cam.p(0, 0, 0)
    stops = [nd[4] for nd in nodes] + [core]
    for k, (a, b) in enumerate(zip(stops, stops[1:])):
        steps = ((5, ".03"), (2.2, ".08"), (1, ".32")) if k < 3 else ((4, ".03"), (1.8, ".08"), (1, ".26"))
        o.append(d3.glow_path(d3.M([a, b]), steps))
        o.append('<path d="%s" stroke="%s" stroke-opacity=".45" stroke-dasharray="4 7"/>' % (d3.M([a, b]), Y))
        if k < 3:
            o.append(_chain_links(a, b))
    x0, y0 = stops[0]
    mv = lambda p, op: "opacity:%s;transform:translate(%spx,%spx)" % (op, n(p[0] - x0), n(p[1] - y0))
    pts = [(0, mv(stops[0], 0)), (P_HOPS[0][0] - .1, mv(stops[0], 0))]
    for k, (t0, t1) in enumerate(P_HOPS):
        pts += [(t0, mv(stops[k], 1)), (t1, mv(stops[k + 1], 1))]
    pts += [(P_HOPS[-1][1] + .08, mv(stops[-1], 0)), (P_HOPS[-1][1] + .11, mv(stops[0], 0))]
    o.append('<g class="%s" opacity="0"><circle cx="%s" cy="%s" r="8" fill="%s" fill-opacity=".16"/><circle cx="%s" cy="%s" '
             'r="4.5" fill="%s" fill-opacity=".38"/><rect x="%s" y="%s" width="4.4" height="4.4" fill="%s"/></g>'
             % (lp.frames(pts), n(x0), n(y0), Y, n(x0), n(y0), Y, n(x0 - 2.2), n(y0 - 2.2), Y))

    arrive = [P_HOPS[0][0]] + [t1 for _, t1 in P_HOPS[:3]]
    for k, (al, kind, wx, wy, base) in sorted(enumerate(nodes), key=lambda e: e[1][4][1]):
        post = d3.Box(cam, wx, wy, 14, 14, 0, 22, P_ROT)
        o.append(post.svg(tint=(".1", ".06", ".03"), edge=".26", top_edge=".46"))
        o.append(post.warm(bands=((0, .2, ".14"), (.2, .42, ".06")), rim=False))
        tx, ty = cam.p(wx, wy, 22)
        o.append('<g transform="translate(%s %s) scale(1 %s)">%s</g>' % (n(tx), n(ty), n(sp, 3), _custody_mark(kind)))
        o.append('<g class="%s" opacity="0"><circle cx="%s" cy="%s" r="20" fill="%s" fill-opacity=".08"/>'
                 '<circle cx="%s" cy="%s" r="11" fill="%s" fill-opacity=".18"/></g>'
                 % (track(lp, [arrive[k]], BLIP_ENV, (0.0,), BLIP_FMT), n(tx), n(ty), Y, n(tx), n(ty), Y))

    # rings, the arrival ping in the core and the beam that carries the sealed record up into the ledger
    o.append(_pulse_rings(lp, cam, 0, 0, P_ZR, P_RINGS, P_PULSE))
    o.append(cam.plane(0, 0, 0) + '<circle class="%s" r="14" stroke="%s" stroke-width="1.6" vector-effect="non-scaling-stroke" '
             'opacity="0"/></g>' % (lp.rings([P_HOPS[-1][1]], .8, 3.4, .85), Y))
    by = cam.p(0, 0, P_Z0 + 12)[1]
    o.append('<g class="%s" opacity="0">%s</g>'
             % (track(lp, [P_HOPS[-1][1] - .05], [(0.0, (0.0,)), (.1, (1.0,)), (.45, (0.0,))], (0.0,), BLIP_FMT),
                d3.glow_path("M%s %sV%s" % (n(core[0]), n(core[1]), n(by)), ((10, ".08"), (5, ".2"), (2, ".95")))))
    # the archived origin block sinks into the core at the end of the cycle
    o.append(cam.plane(0, 0, P_ZR) + '<circle class="%s" r="40" stroke="%s" stroke-width="1.6" vector-effect="non-scaling-stroke" '
             'opacity="0"/></g>' % (lp.rings([P_SHIFT[1] - .35], .3 + PED_T - P_SHIFT[1] - .05, 2.2, .6), Y))

    # the ledger: four blocks, each in its slot, bobbing together; the stack settles one pitch per cycle
    o.append('<g class="%s">' % _bob(lp, P_BOB, PED_T))
    shift = P_PITCH * cp
    s0, s1 = P_SHIFT
    rest = "transform:translateY(0px)"
    down = "transform:translateY(%spx)" % n(shift)
    lift = P_PITCH * cp * 1.6
    cls = [lp.frames([(0, "opacity:1;" + rest), (s0, "opacity:1;" + rest), (s1, "opacity:0;" + down)]),
           lp.frames([(0, rest), (s0, rest), (s1, down)]),
           lp.frames([(0, rest), (s0, rest), (s1, down)]),
           lp.frames([(0, "opacity:0;transform:translateY(-%spx)" % n(lift)), (P_DROP, "opacity:0;transform:translateY(-%spx)" % n(lift)),
                      (P_DROP + .15, "opacity:1;transform:translateY(-%spx)" % n(lift * .8)), (P_LOCK, "opacity:1;" + rest),
                      (P_LOCK + .08, "opacity:1;transform:translateY(-1.5px)"), (P_LOCK + .2, "opacity:1;" + rest),
                      (s0, "opacity:1;" + rest), (s1, "opacity:1;" + down)])]
    blocks = []
    flash_env = [(0.0, (0.0,)), (.1, (1.0,)), (.55, (0.0,))]
    for k in range(4):
        b, svg = _ledger_block(cam, P_Z0 + k * P_PITCH)
        blocks.append(b)
        o.append('<g class="%s">%s' % (cls[k], svg))
        o.append('<g class="%s" opacity="0">%s%s</g>'
                 % (track(lp, [P_TRACE[3 - k]], flash_env, (0.0,), BLIP_FMT),
                    d3.glow_path(d3.M(b.top_front()), ((8, ".08"), (4, ".2"), (1.6, ".95"))),
                    b.warm(bands=((0, .5, ".16"), (.5, 1, ".06")), rim=False)))
        if k == 3:
            o.append('<g class="%s" opacity="0">%s</g>'
                     % (track(lp, [P_LOCK], [(0.0, (0.0,)), (.06, (1.0,)), (.7, (0.0,))], (0.0,), BLIP_FMT),
                        d3.glow_path(b.bottom_edges(), ((12, ".1"), (6, ".24"), (2.2, "1")))))
        o.append('</g>')

    # hash links between neighbouring blocks at the visible vertical edges; they step aside while the stack settles
    # (the top gap only links once the new block has locked, and is empty again when the cycle restarts)
    link = lp.frames([(0, "opacity:1"), (s0 - .05, "opacity:1"), (s0 + .15, "opacity:0"), (s1 - .05, "opacity:0"), (s1 + .3, "opacity:1")])
    link_top = lp.frames([(0, "opacity:0"), (P_LOCK, "opacity:0"), (P_LOCK + .15, "opacity:1"), (s0 - .05, "opacity:1"),
                          (s0 + .15, "opacity:0")])
    for ks, lcls in ((range(2), link), (range(2, 3), link_top)):
        lk_d = []
        for k in ks:
            lo, hi = blocks[k], blocks[k + 1]
            verts = sorted({v for _, i, j in lo.faces for v in (i, j)})
            lk_d += [d3.M([lo.top[v], hi.bot[v]]) for v in verts]
        o.append('<g class="%s">%s</g>' % (lcls, d3.glow_path("".join(lk_d), ((5, ".1"), (2.2, ".8")))))

    # lock: sparkle on the new block and a padlock badge beside it
    top = blocks[3]
    ax, ay = top.apex()
    sp_pts = [(0, "opacity:0;transform:scale(0) rotate(0deg)"), (P_LOCK, "opacity:0;transform:scale(0) rotate(0deg)"),
              (P_LOCK + .25, "opacity:1;transform:scale(1) rotate(45deg)"), (P_LOCK + .8, "opacity:0;transform:scale(.3) rotate(90deg)"),
              (P_LOCK + .83, "opacity:0;transform:scale(0) rotate(0deg)")]
    o.append(d3.sparkle(ax, ay, .9, lp.frames(sp_pts, "ease-out")))
    rx, ry = max(top.top, key=lambda q: q[0])
    badge = track(lp, [P_LOCK + .1], [(0.0, (0.0, 0.0)), (.3, (1.0, 1.0)), (1.4, (1.0, 1.0)), (1.75, (0.0, 1.0))], (0.0, 0.0), PING_FMT)
    o.append('<g transform="translate(%s %s)"><g class="%s"><circle r="24" fill="%s" fill-opacity=".08"/>'
             '<circle r="16" fill="%s" stroke="%s" stroke-width="1.6"/><path d="M-4.5 -2V-5.5A4.5 4.5 0 0 1 4.5 -5.5V-2" '
             'stroke="%s" stroke-width="2"/><rect x="-7" y="-2" width="14" height="10.5" rx="1.5" fill="%s"/>'
             '<path d="M0 2.2V4.6" stroke="%s" stroke-width="2"/></g></g>' % (n(rx + 34), n(ry - 26), badge, Y, K, Y, Y, Y, K))
    o.append('</g>')

    # trust score dial: lit ticks, a head tick that flashes when the lineage check lands, and a ping
    dx, dy, R = 112, 120, 36
    lx, ly = min(blocks[2].top, key=lambda q: q[0])
    o.append('<path d="M%s %sL%s %s" stroke="%s" stroke-opacity=".22" stroke-dasharray="3 6"/>' % (n(dx + R + 8), n(dy + 12), n(lx - 8), n(ly), W))
    o.append(d3.halo(dx, dy, ((64, ".02"), (46, ".03"))))
    o.append('<circle cx="%d" cy="%d" r="%d" fill="%s" stroke="%s" stroke-opacity=".12"/>' % (dx, dy, R + 10, K, W))
    lit, dim_, head = [], [], ""
    for i in range(P_TICKS):
        a = math.radians(135 + 270.0 * i / (P_TICKS - 1))
        seg = "M%s %sL%s %s" % (n(dx + (R - 7) * math.cos(a)), n(dy + (R - 7) * math.sin(a)), n(dx + R * math.cos(a)), n(dy + R * math.sin(a)))
        if i < P_LIT:
            lit.append(seg)
        else:
            dim_.append(seg)
        if i == P_LIT - 1:
            head = seg
    o.append('<path d="%s" stroke="%s" stroke-opacity=".16" stroke-width="2.4"/>' % ("".join(dim_), W))
    o.append(d3.glow_path("".join(lit), ((6, ".07"), (2.4, ".9"))))
    o.append('<path d="M%d %sL%s %dL%d %sL%s %dZ" stroke="%s" stroke-opacity=".5" stroke-width="1.4"/>'
             % (dx, n(dy - 13), n(dx + 11.3), dy, dx, n(dy + 13), n(dx - 11.3), dy, Y))
    o.append('<path d="M%s %sH%sM%s %sH%sM%s %sH%s" stroke="%s" stroke-opacity=".7" stroke-width="1.6"/>'
             % (n(dx - 4), n(dy - 3.5), n(dx + 4), n(dx - 5.5), n(dy), n(dx + 5.5), n(dx - 4), n(dy + 3.5), n(dx + 4), Y))
    o.append('<g class="%s" opacity="0">%s</g>'
             % (track(lp, [P_SCORE[1]], [(0.0, (0.0,)), (.1, (1.0,)), (.9, (0.0,))], (0.0,), BLIP_FMT),
                d3.glow_path(head, ((12, ".12"), (6, ".3"), (3, "1")), color=W)))
    o.append('<g transform="translate(%d %d)"><circle class="%s" r="%d" stroke="%s" stroke-width="1.6" '
             'vector-effect="non-scaling-stroke" opacity="0"/></g>' % (dx, dy, lp.rings([P_SCORE[1]], .9, 1.5, .8), R + 10, Y))
    # the lineage result rides from the stack to the dial
    o.append('<g class="%s" opacity="0"><circle cx="%s" cy="%s" r="6" fill="%s" fill-opacity=".22"/>'
             '<rect x="%s" y="%s" width="4" height="4" fill="%s"/></g>'
             % (lp.moves([(P_SCORE[0], P_SCORE[1] - P_SCORE[0])], dx + R + 8 - (lx - 8), dy + 12 - ly, .2),
                n(lx - 8), n(ly), Y, n(lx - 10), n(ly - 2), Y))
    o.append('</svg>')
    return "".join(o)


# ---------------------------------------------------------------- page hooks
BUILDERS = {"geo": (geo_svg, GEO_T), "aura": (aura_svg, AURA_T), "ledger": (pedigree_svg, PED_T)}


def figure(key):
    """Figure for an engine key from build.ENGINES, or None if that engine still uses its static image."""
    b = BUILDERS.get(key)
    if not b:
        return None
    return '<figure class="lpan" data-loop data-engine="%s">%s</figure>' % (key, b[0]())


if __name__ == "__main__":
    for k, (fn, T) in BUILDERS.items():
        print("engine %-6s svg %.2f KB, loop %gs" % (k, len(fn().encode()) / 1024.0, T))
