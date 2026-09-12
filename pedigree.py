# -*- coding: utf-8 -*-
"""Data pedigree packet flow, looping (institutions.html, "Six stages, from source to ledger.").

A flat rail with the six stage nodes, drawn inside the white Data pedigree card above the stage list.
One evidence packet rides the rail from source capture to DLT registration: at every node it pauses,
the node rings and turns yellow, and the matching number badge in the list below pulses in step.
At the ledger it is absorbed and a new block is appended to the chain. Loop 8s (loopkit.py):
  0.3s packet appears at 01, departs 0.6s, arrives at 02..06 at 1.3 / 2.35 / 3.4 / 4.45 / 5.5s
  (0.35s dwell per node), 5.5-5.8s absorbed, 5.75s block appended, hold, 7.2-7.7s the trail clears, 8s loop.
Reduced motion or no CSS animation: the whole trail is drawn, every node visited, the chain complete.
The rail stays left to right under dir=rtl on purpose, like every other pipeline diagram on the site.
"""
import loopkit as lk

T = 8.0
Y, D, K = "#FFD400", "#E6BF00", "#0A0A09"
X0, STEP, RY, R = 44, 110.4, 78, 17
DEPART0, TRAVEL, DWELL = .6, .7, .35
EXIT = (7.2, 7.7)
# 01 capture target, 02 authenticated check, 03 cleaning funnel, 04 cross validation,
# 05 twin integration cube, 06 ledger blocks (on the yellow node)
GLYPHS = ['<circle r="6" stroke="%s" stroke-width="1.6" fill="none"/><circle r="2.2" fill="%s"/>' % (K, K),
          '<path d="M-6 .5l4 4 8-8.5" stroke="%s" stroke-width="2" fill="none"/>' % K,
          '<path d="M-6.5 -5H6.5L1.6 1V6.2L-1.6 4.4V1Z" stroke="%s" stroke-width="1.5" fill="none"/>' % K,
          '<path d="M-6 -5L6 5M-6 5L6 -5" stroke="%s" stroke-width="1.7"/>' % K,
          '<path d="M0 -6.5L5.8 -3.2V3.2L0 6.5L-5.8 3.2V-3.2ZM-5.8 -3.2L0 0L5.8 -3.2M0 0V6.5" stroke="%s" stroke-width="1.4" fill="none"/>' % K,
          '<path d="M-6.5 -6.5h5.5v5.5h-5.5zM1 1h5.5v5.5H1zM-3.75 -1V3.75H1" stroke="%s" stroke-width="1.5" fill="none"/>' % K]


def arrivals():
    return [DEPART0 + TRAVEL + k * (TRAVEL + DWELL) for k in range(5)]     # nodes 02..06


def build():
    """(svg markup, [loop class for each list badge 01..06])"""
    lp = lk.Loop("pd", T, "institutions: data pedigree packet flow, loop %gs" % T)
    n = lk.num
    xs = [X0 + i * STEP for i in range(6)]
    arr = arrivals()
    o = ['<svg fill="none" class="lps pd-rail" viewBox="0 0 640 124" aria-hidden="true" focusable="false">']
    o.append('<path d="M%s %dH%s" stroke="%s" stroke-opacity=".14" stroke-width="2"/>' % (n(xs[0]), RY, n(xs[-1]), K))
    # the trail: each segment draws while the packet travels it
    for k in range(5):
        t0 = DEPART0 if k == 0 else arr[k - 1] + DWELL
        o.append('<path class="%s" pathLength="1" stroke-dasharray="1" d="M%s %dH%s" stroke="%s" stroke-width="3"/>'
                 % (lp.win(lk.DRAW, t0, t0 + TRAVEL, *EXIT, ease="linear"), n(xs[k] + R), RY, n(xs[k + 1] - R), Y))
    # ledger chain above node 06: two blocks already registered, the third appended each cycle
    bx = xs[5]
    o.append('<path d="M%s %dV%d" stroke="%s" stroke-opacity=".3" stroke-width="1.5" stroke-dasharray="2 3"/>'
             % (n(bx), RY - R - 3, 40, K))
    o.append('<path d="M%s 26h8M%s 26h8" stroke="%s" stroke-opacity=".3" stroke-width="1.5"/>' % (n(bx - 58), n(bx - 30), K))
    for j, x in enumerate((bx - 78, bx - 50, bx - 22)):
        cls = ' class="%s"' % lp.win(("opacity:0;transform:translateY(-14px)", "opacity:1;transform:none",
                                      "opacity:0;transform:none"), arr[4] + .25, arr[4] + .65, *EXIT) if j == 2 else ""
        o.append('<rect%s x="%s" y="14" width="44" height="24" rx="2" fill="%s" stroke="%s" stroke-width="1.5"/>'
                 % (cls, n(x), Y if j == 2 else "#fff", D if j == 2 else K))
        o.append('<path d="M%s 26h12" stroke="%s" stroke-opacity=".45" stroke-width="1.5"/>' % (n(x + 16), K))
    # nodes
    for i, x in enumerate(xs):
        last = i == 5
        o.append('<g transform="translate(%s %d)">' % (n(x), RY))
        o.append('<circle class="%s" r="%d" stroke="%s" stroke-width="1.6" fill="none" opacity="0"/>'
                 % (lp.rings([.3 if i == 0 else arr[i - 1]], .8, 2.1), R, D))
        o.append('<circle r="%d" fill="%s" stroke="%s" stroke-width="1.5" stroke-opacity="%s"/>'
                 % (R, Y if last else "#fff", D if last else K, "1" if last else ".28"))
        if not last:   # visited: the node turns yellow and stays yellow until the trail clears
            o.append('<circle class="%s" r="%d" fill="%s" stroke="%s" stroke-width="1.5"/>'
                     % (lp.win(lk.FADE, (.3 if i == 0 else arr[i - 1]) - .05, (.3 if i == 0 else arr[i - 1]) + .2, *EXIT), R, Y, D))
        o.append(GLYPHS[i] + '</g>')
    # the packet: appears at 01, rides the rail with a dwell at every node, absorbed at 06
    tr = lambda x, s=1: "transform:translate(%spx,0px) scale(%s)" % (n(x - xs[0]), n(s))
    pts = [(0, "opacity:0;" + tr(xs[0], 0)), (.3, "opacity:0;" + tr(xs[0], 0)), (.5, "opacity:1;" + tr(xs[0]))]
    for k in range(5):
        dep = DEPART0 if k == 0 else arr[k - 1] + DWELL
        pts += [(dep, "opacity:1;" + tr(xs[k])), (arr[k], "opacity:1;" + tr(xs[k + 1]))]
    pts += [(arr[4] + .3, "opacity:0;" + tr(xs[5], 0))]
    o.append('<g transform="translate(%s %d)"><path class="%s" d="M0 -9.5L9.5 0L0 9.5L-9.5 0Z" '
             'fill="%s" stroke="%s" stroke-width="1.6" opacity="0"/></g>'
             % (n(xs[0]), RY - 30, lp.frames(pts, "cubic-bezier(.5,0,.4,1)"), Y, K))
    o.append('</svg>')
    # the list badges pulse in step: each one needs its own timing, so one frames() per stage
    badges = []
    for t in [.3] + arr:
        badges.append(lp.frames([(0, "transform:none"), (t - .02, "transform:none"), (t + .16, "transform:scale(1.22)"),
                                 (t + .55, "transform:none")], "cubic-bezier(.3,.7,.4,1)"))
    return "".join(o), badges


if __name__ == "__main__":
    s, bd = build()
    print("pedigree svg: %.2f KB, loop %gs, badges %s" % (len(s.encode()) / 1024.0, T, bd))
