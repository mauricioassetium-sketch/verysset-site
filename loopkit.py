# -*- coding: utf-8 -*-
"""Shared helper for the looping illustrations (round 6).

Users: mirror.py (how-it-works digital twin), pedigree.py (institutions data pedigree strip),
rwa.py (index hero "real world assets." underline), jurisdiction.py (institutions supervisor).

Why generated keyframes: every loop sequences many parts that enter at different moments but must
all reset together at the end of the cycle. A shared keyframe plus animation-delay cannot do that
(a delay shifts the whole cycle, reset included), so each part gets its own keyframes with its
timing encoded as percentages of one cycle, and every part runs the same duration, infinite.
build.py collects every registered Loop and writes the CSS into assets/site.css between the
LOOPS:BEGIN / LOOPS:END markers. Never hand edit that block: edit the module, run build.py.

Rules of the road:
  * transform and opacity only, plus stroke-dashoffset for a few short outline draws.
  * every animation rule sits inside @media (prefers-reduced-motion:no-preference), so under
    reduce (or when CSS animations are unsupported) the markup's base styles ARE the final,
    composed frame. Parts that must be hidden in that static frame carry opacity="0".
  * site.js adds .lp-off to a [data-loop] element while it is off screen, which pauses it.
  * an SVG element animated with a CSS transform must not carry a transform attribute
    (CSS would override it): wrap it in a positioned <g> instead.
"""
import re

EASE = "cubic-bezier(.45,0,.25,1)"
_LOOPS = []

# (hidden, visible, after exit)
FADE = ("opacity:0", "opacity:1")
DRAW = ("opacity:0;stroke-dashoffset:1", "opacity:1;stroke-dashoffset:0", "opacity:0;stroke-dashoffset:0")
DROP = ("opacity:0;transform:translateY(-16px)", "opacity:1;transform:none", "opacity:0;transform:none")
POP = ("opacity:0;transform:scale(0)", "opacity:1;transform:none", "opacity:0;transform:none")


def num(v, dec=2):
    s = ("%%.%df" % dec) % v
    return s.rstrip("0").rstrip(".") if "." in s else s


def _b36(i):
    a = "0123456789abcdefghijklmnopqrstuvwxyz"
    return a[i] if i < 36 else _b36(i // 36) + a[i % 36]


class Loop:
    def __init__(self, name, T, note=""):
        self.name, self.T, self.note = name, float(T), note
        self.anims = []            # [(animation name, keyframes body, easing)]
        self._seen = {}
        _LOOPS[:] = [lp for lp in _LOOPS if lp.name != name]   # a rebuilt svg replaces its loop
        _LOOPS.append(self)

    def frames(self, pts, ease=EASE):
        """pts: [(seconds, "decls"), ...] in time order. The first state is held from 0s and the
           last one to the end of the cycle. Returns the class name that plays it."""
        seq = [(0.0, pts[0][1])] + [(min(max(float(t), 0.0), self.T), d) for t, d in pts] + [(self.T, pts[-1][1])]
        groups = []
        for t, d in seq:
            p = num(100.0 * t / self.T) + "%"
            if groups and groups[-1][1] == d:
                if groups[-1][0][-1] != p:
                    groups[-1][0].append(p)
            else:
                groups.append(([p], d))
        # a run of identical states only needs its first and last offset
        body = "".join("%s{%s}" % (",".join([g[0]] if len(g) == 1 else [g[0], g[-1]]), d) for g, d in groups)
        key = (body, ease)
        if key not in self._seen:
            nm = self.name + _b36(len(self._seen))
            self._seen[key] = nm
            self.anims.append((nm, body, ease))
        return self._seen[key]

    def win(self, kind, t0, t1, t2=None, t3=None, ease=EASE):
        """Enter between t0 and t1, optionally exit between t2 and t3, hidden again until the cycle ends."""
        hid, vis = kind[0], kind[1]
        out = kind[2] if len(kind) > 2 else hid
        pts = [(0, hid), (t0, hid), (t1, vis)]
        if t2 is not None:
            pts += [(t2, vis), (t3, out)]
        return self.frames(pts, ease)

    def moves(self, trips, dx, dy=0.0, edge=.18, ease="linear"):
        """A packet: for each (t0, dur) it fades in, travels (dx, dy), fades out, and jumps home unseen."""
        tr = lambda f: "transform:translate(%spx,%spx)" % (num(dx * f), num(dy * f))
        pts = [(0, "opacity:0;" + tr(0))]
        for t0, dur in trips:
            pts += [(t0, "opacity:0;" + tr(0)), (t0 + dur * edge, "opacity:1;" + tr(edge)),
                    (t0 + dur * (1 - edge), "opacity:1;" + tr(1 - edge)), (t0 + dur, "opacity:0;" + tr(1)),
                    (t0 + dur + .03, "opacity:0;" + tr(0))]
        return self.frames(pts, ease)

    def rings(self, times, dur=.8, s1=3.0, peak=.9, ease="cubic-bezier(.2,.6,.3,1)"):
        """An expanding ring for each start time (keep t + dur + .03 before the next start)."""
        pts = [(0, "opacity:0;transform:scale(1)")]
        for t in times:
            pts += [(t, "opacity:0;transform:scale(1)"), (t + .04, "opacity:%s;transform:scale(1)" % num(peak)),
                    (t + dur, "opacity:0;transform:scale(%s)" % num(s1)), (t + dur + .03, "opacity:0;transform:scale(1)")]
        return self.frames(pts, ease)

    def flash(self, times, peak=.6, rise=.15, fall=.6, ease="ease-out"):
        """Opacity blips for an overlay that is hidden in the static frame."""
        pts = [(0, "opacity:0")]
        for t in times:
            pts += [(t, "opacity:0"), (t + rise, "opacity:%s" % num(peak)), (t + rise + fall, "opacity:0")]
        return self.frames(pts, ease)

    def css(self):
        T = num(self.T)
        rules = ",".join("." + n for n, b, e in self.anims) + "{transform-box:fill-box;transform-origin:center}"
        rules += "".join(".%s{animation:%s %ss %s infinite}" % (n, n, T, e) for n, b, e in self.anims)
        kfs = "".join("\n@keyframes %s{%s}" % (n, b) for n, b, e in self.anims)
        return "/* %s */\n@media (prefers-reduced-motion:no-preference){\n%s%s\n}" % (self.note, rules, kfs)


def inject(path):
    """Write every registered loop into site.css between its generated markers."""
    block = ("/* ==== LOOPS:BEGIN generated by build.py from loopkit.py. Do not hand edit. ==== */\n"
             + "\n".join(lp.css() for lp in _LOOPS if lp.anims) + "\n/* ==== LOOPS:END ==== */")
    src = open(path, encoding="utf-8").read()
    pat = re.compile(r"/\* ==== LOOPS:BEGIN.*?==== \*/.*?/\* ==== LOOPS:END ==== \*/", re.S)
    if not pat.search(src):
        raise SystemExit("site.css is missing the LOOPS:BEGIN / LOOPS:END markers")
    open(path, "w", encoding="utf-8").write(pat.sub(lambda _m: block, src))
    return len(block.encode("utf-8"))


def iso(cx, yc, hw, hh, t):
    """Isometric box, top face centred on (cx, yc): (top, left, right) polygon points and the visible outline."""
    lx, rx, by = cx - hw, cx + hw, yc + hh + t
    P = lambda *pts: " ".join("%s,%s" % (num(x), num(y)) for x, y in pts)
    top = P((lx, yc), (cx, yc - hh), (rx, yc), (cx, yc + hh))
    left = P((lx, yc), (cx, yc + hh), (cx, by), (lx, yc + t))
    right = P((cx, yc + hh), (rx, yc), (rx, yc + t), (cx, by))
    outline = "M%s %sL%s %sL%s %sL%s %sZM%s %sV%sL%s %sL%s %sV%sM%s %sV%s" % tuple(num(v) for v in (
        lx, yc, cx, yc - hh, rx, yc, cx, yc + hh, lx, yc, yc + t, cx, by, rx, yc + t, yc, cx, yc + hh, by))
    return top, left, right, outline


def durations():
    return [(lp.name, lp.T, lp.note) for lp in _LOOPS if lp.anims]
