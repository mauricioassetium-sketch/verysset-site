# -*- coding: utf-8 -*-
"""Looping "real world assets." underline (index.html hero h1).

The words stay live HTML text inside the <em> (translatable, selectable, Clash Display from the h1).
Only the yellow bar is graphic: an inline SVG absolutely placed under the em, so its width is always
the text width at every viewport and in every language. No viewBox: the rects fill 100% of the box and
the verification dots sit at percentage positions with an em radius, so nothing ever stretches.

Loop 5s (loopkit.py):
  0.15-1.35s  the bar draws in from the left edge (scaleX 0 to 1, origin left) over a pale track;
              each verification dot pops in the moment the drawing edge reaches it
  1.35-3.85s  hold (2.5s); 1.75s on, the four dots blink softly in sequence, left to right
  3.85-4.30s  subtle dim of the bar and dots
  4.30-4.80s  re-draw: the bar retracts toward the right end, revealing the pale track, dots go out
              as the edge passes them; 4.95s parked at zero width, 5s the draw starts again
Reduced motion or no CSS animation: the markup is the static frame, bar fully drawn, dots resting.
Under dir=rtl site.css mirrors the whole SVG, so the bar draws right to left under Arabic.
"""
import loopkit as lk

T = 5.0
Y, TRACK, K = "#FFD400", "#FFF3B0", "#0A0A09"
DRAW = (.15, 1.35)            # scaleX 0 -> 1
HOLD_END = 3.85               # 2.5s hold
DIM = (3.85, 4.30)            # bar opacity 1 -> DIM_O
RETRACT = (4.30, 4.80)        # bar exits toward the right end
PARK = 4.95                   # back to zero width at the left edge, unseen
DIM_O = .55
DOTS = (.16, .39, .62, .85)   # fraction of the bar width
DOT_R = ".038em"
DOT_CY = 70                   # % of the bar height: below the headline baseline, clear of the glyphs
BLINK0, BLINK_STEP = 1.75, .38
EASE_BAR = (.65, 0, .35, 1)
EASE_DOT = "cubic-bezier(.3,.7,.4,1)"


def _bez(a, b, s):
    return 3 * (1 - s) * (1 - s) * s * a + 3 * (1 - s) * s * s * b + s * s * s


def when(progress, ease=EASE_BAR):
    """Time fraction at which a cubic-bezier easing reaches this progress (bisection, monotone curves)."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if _bez(ease[1], ease[3], mid) < progress:
            lo = mid
        else:
            hi = mid
    return _bez(ease[0], ease[2], (lo + hi) / 2)


def css_ease(e):
    return "cubic-bezier(%s)" % ",".join(lk.num(v) for v in e)


def em(text="real world assets."):
    """The hero <em>: live text plus the looping underline SVG."""
    lp = lk.Loop("rw", T, "index: hero real world assets. underline, loop %gs" % T)
    n = lk.num
    bar = lambda op, tx, sx: "opacity:%s;transform:translateX(%s%%) scaleX(%s)" % (n(op), n(tx), n(sx))
    fill = lp.frames([(0, bar(1, 0, 0)), (DRAW[0], bar(1, 0, 0)), (DRAW[1], bar(1, 0, 1)),
                      (HOLD_END, bar(1, 0, 1)), (DIM[1], bar(DIM_O, 0, 1)),
                      (RETRACT[1], bar(DIM_O, 100, 0)), (PARK, bar(1, 0, 0))], css_ease(EASE_BAR))
    o = ['<svg class="rwa-u" data-loop aria-hidden="true" focusable="false">',
         '<rect width="100%%" height="100%%" fill="%s"/>' % TRACK,
         '<rect class="rwa-f %s" width="100%%" height="100%%" fill="%s"/>' % (fill, Y)]
    # dots rest solid near-black (flat); a blink is a brief soft dip, then a small swell back to rest
    hid, rest, dim = "opacity:0;transform:scale(0)", "opacity:1;transform:scale(1)", "opacity:.4;transform:scale(1)"
    for i, x in enumerate(DOTS):
        t_in = DRAW[0] + (DRAW[1] - DRAW[0]) * when(x)          # the drawing edge reaches the dot
        t_out = RETRACT[0] + (RETRACT[1] - RETRACT[0]) * when(x)  # the retracting edge passes it
        blink = BLINK0 + i * BLINK_STEP
        pts = [(0, hid), (t_in - .02, hid), (t_in + .16, "opacity:1;transform:scale(1.45)"), (t_in + .45, rest),
               (blink, rest), (blink + .18, "opacity:.35;transform:scale(.8)"),
               (blink + .42, "opacity:1;transform:scale(1.4)"), (blink + .75, rest),
               (DIM[0], rest), (DIM[1], dim), (t_out - .08, dim), (t_out + .04, hid)]
        o.append('<circle class="%s" cx="%s%%" cy="%s%%" r="%s" fill="%s"/>'
                 % (lp.frames(pts, EASE_DOT), n(100 * x), DOT_CY, DOT_R, K))
    o.append('</svg>')
    return "<em>%s%s</em>" % (text, "".join(o))


if __name__ == "__main__":
    s = em()
    print("rwa em: %.2f KB, loop %gs" % (len(s.encode()) / 1024.0, T))
    for x in DOTS:
        print("dot %.2f  in %.2fs  out %.2fs" % (x, DRAW[0] + (DRAW[1] - DRAW[0]) * when(x),
                                               RETRACT[0] + (RETRACT[1] - RETRACT[0]) * when(x)))
