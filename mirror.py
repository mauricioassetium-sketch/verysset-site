# -*- coding: utf-8 -*-
"""The verifiable digital twin, looping (how-it-works.html, "The asset, mirrored by its own evidence.").

One flat inline SVG on near-black. The physical asset stands left of a mirror axis and never moves;
its twin is rebuilt on the right, one layer per evidence channel, then verified and kept current.
Loop 9s, every part on the same cycle (loopkit.py):
  0.2-0.7s  satellite link draws to the rooftop sensor, the sensor ripples before every packet
  0.5-1.8s  a scan plane sweeps both sides of the mirror
  1.0 / 1.8 / 2.6s  evidence packets cross the axis, landing the bottom / middle / top layer
  3.8-4.5s  the twin is verified: link, yellow badge, ring
  5.2 / 5.9 / 6.6s  live events keep crossing, each one flashes the layer it updates
  7.9-8.5s  the twin clears (the asset stays), 9s the cycle restarts
Reduced motion or no CSS animation: the markup is the composed, verified twin.
"""
import loopkit as lk

T = 9.0
Y, K, W = "#FFD400", "#0A0A09", "#fff"
CXA, CXT = 160, 440                 # asset / twin axis
TOP, HW, HH, H = 196, 84, 42, 112   # top face centre y, half width, half height, full height
LT, GAP = 30, 11                    # twin layer thickness and gap: 3 * 30 + 2 * 11 = 112
EXIT = (7.9, 8.5)
DROP = ("opacity:0;transform:translateY(-26px)", "opacity:1;transform:none", "opacity:0;transform:none")
# per twin layer, top to bottom: build packet start, live update packet start
TRIPS = [(2.6, 5.9), (1.8, 5.2), (1.0, 6.6)]
PACKET = .8
RIPPLES = [.5, 1.3, 2.1, 4.7, 5.45, 6.2]


def svg():
    lp = lk.Loop("mr", T, "how-it-works: verifiable digital twin, loop %gs" % T)
    n = lk.num
    o = ['<svg fill="none" class="lps" viewBox="0 0 600 470" role="img" aria-label="Verifiable digital twin of a real world asset" '
         'focusable="false">']
    o.append('<path d="%s" stroke="%s" stroke-opacity=".09" stroke-width="2"/>'
             % ("".join("M%d %dh0" % (x, y) for x in range(20, 600, 40) for y in range(35, 470, 40)), W))
    o.append('<path d="M300 30V448" stroke="%s" stroke-opacity=".22" stroke-dasharray="2 7"/>' % W)
    fy = TOP + H                     # footprint centre
    for cx in (CXA, CXT):
        o.append('<path d="M%d %dL%d %dL%d %dL%d %dZ" fill="%s" fill-opacity=".03" stroke="%s" stroke-opacity=".14"/>'
                 % (cx - 124, fy, cx, fy - 62, cx + 124, fy, cx, fy + 62, W, W))

    # scan plane: sweeps both sides once per cycle, hidden in the static frame
    sc = lp.frames([(0, "opacity:0;transform:translateY(0px)"), (.5, "opacity:0;transform:translateY(0px)"),
                    (.7, "opacity:1;transform:translateY(30px)"), (1.6, "opacity:1;transform:translateY(196px)"),
                    (1.8, "opacity:0;transform:translateY(226px)"), (1.83, "opacity:0;transform:translateY(0px)")],
                   "linear")
    o.append('<g class="%s" opacity="0"><rect x="40" y="140" width="520" height="12" fill="%s" fill-opacity=".08"/>'
             '<path d="M40 152H560" stroke="%s" stroke-opacity=".7"/></g>' % (sc, Y, Y))

    # the physical asset: always present
    top, left, right, outline = lk.iso(CXA, TOP, HW, HH, H)
    fl = "".join("M%d %dL%d %dM%d %dL%d %d" % (CXA - HW, TOP + d, CXA, TOP + HH + d, CXA, TOP + HH + d, CXA + HW, TOP + d)
                 for d in (28, 56, 84))
    o.append('<polygon points="%s %s %s" fill="%s"/>' % (top, left, right, K))     # opaque base: nothing shows through
    o.append('<polygon points="%s" fill="%s" fill-opacity=".14"/><polygon points="%s" fill="%s" fill-opacity=".05"/>'
             '<polygon points="%s" fill="%s" fill-opacity=".09"/><path d="%s" stroke="%s" stroke-opacity=".2"/>'
             '<path d="%s" stroke="%s" stroke-opacity=".72" stroke-width="1.4"/>'
             % (top, W, left, W, right, W, fl, W, outline, W))
    o.append('<path d="M%d %dV152" stroke="%s" stroke-opacity=".5"/>' % (CXA, TOP, W))
    o.append('<circle class="%s" cx="%d" cy="146" r="6" stroke="%s" stroke-width="1.5" fill="none" opacity="0"/>'
             % (lp.rings(RIPPLES, .7, 3.2), CXA, Y))
    o.append('<circle cx="%d" cy="146" r="5" fill="%s"/>' % (CXA, Y))

    # satellite: bobs, its link draws in and clears with the twin
    bob = lp.frames([(0, "transform:translateY(0px)"), (2.25, "transform:translateY(-6px)"), (4.5, "transform:translateY(0px)"),
                     (6.75, "transform:translateY(-6px)"), (9, "transform:translateY(0px)")], "ease-in-out")
    o.append('<path class="%s" pathLength="1" stroke-dasharray="1" d="M84 82L154 138" stroke="%s" stroke-opacity=".75"/>'
             % (lp.win(lk.DRAW, .2, .7, *EXIT), Y))
    o.append('<g transform="translate(66 64) rotate(-28)"><g class="%s">'
             '<rect x="-8" y="-6" width="16" height="12" rx="1.5" fill="%s"/>'
             '<rect x="-31" y="-5" width="19" height="10" fill="%s" fill-opacity=".1" stroke="%s" stroke-opacity=".7"/>'
             '<rect x="12" y="-5" width="19" height="10" fill="%s" fill-opacity=".1" stroke="%s" stroke-opacity=".7"/>'
             '<path d="M-21.5 -5V5M21.5 -5V5M-12 0H-8M8 0H12" stroke="%s" stroke-opacity=".7"/></g></g>'
             % (bob, W, W, W, W, W, W))

    # evidence channels across the mirror and their packets
    for i, (build, update) in enumerate(TRIPS):
        y = TOP + i * (LT + GAP) + LT // 2
        o.append('<path d="M252 %dH348" stroke="%s" stroke-opacity=".3" stroke-dasharray="2 5"/>'
                 '<circle cx="252" cy="%d" r="2.5" fill="%s" fill-opacity=".6"/><circle cx="348" cy="%d" r="2.5" fill="%s" fill-opacity=".6"/>'
                 % (y, Y, y, Y, y, Y))
        o.append('<rect class="%s" x="246" y="%d" width="12" height="8" rx="1" fill="%s" opacity="0"/>'
                 % (lp.moves([(build, PACKET), (update, PACKET)], 96), y - 4, Y))

    # the twin: bottom layer first so upper layers overlap it
    for i in (2, 1, 0):
        yc = TOP + i * (LT + GAP)
        t0 = TRIPS[i][0] + .6
        top, left, right, outline = lk.iso(CXT, yc, HW, HH, LT)
        o.append('<g class="%s"><polygon points="%s" fill="%s"/><polygon points="%s" fill="%s"/><polygon points="%s" fill="%s"/>'
                 '<polygon points="%s" fill="%s" fill-opacity=".22"/>'
                 '<polygon points="%s" fill="%s" fill-opacity=".05"/><polygon points="%s" fill="%s" fill-opacity=".13"/>'
                 '<path class="%s" pathLength="1" stroke-dasharray="1" d="%s" stroke="%s" stroke-width="1.5"/>'
                 '<polygon class="%s" points="%s" fill="%s" opacity="0"/></g>'
                 % (lp.win(DROP, t0, t0 + .6, *EXIT), top, K, left, K, right, K, top, Y, left, W, right, Y,
                    lp.win(lk.DRAW, t0, t0 + .7, *EXIT), outline, Y,
                    lp.flash([TRIPS[i][1] + PACKET - .05], .55, .15, .7), top, Y))

    # verification: link, badge, ring
    o.append('<path class="%s" pathLength="1" stroke-dasharray="1" d="M%d 131V150" stroke="%s" stroke-opacity=".8"/>'
             % (lp.win(lk.DRAW, 3.8, 4.1, *EXIT), CXT, Y))
    o.append('<g transform="translate(%d 112)"><circle class="%s" r="16" stroke="%s" stroke-width="1.5" fill="none" opacity="0"/>'
             '<g class="%s"><circle r="16" fill="%s"/><path d="M-7 .5l4.6 4.6 9.2-9.6" stroke="%s" stroke-width="2.6" fill="none"/></g></g>'
             % (CXT, lp.rings([4.3], 1.1, 2.6), Y, lp.win(lk.POP, 4.0, 4.5, *EXIT), Y, K))
    o.append('</svg>')
    return "".join(o)


def figure():
    return '<figure class="lpan" data-loop>%s</figure>' % svg()


if __name__ == "__main__":
    s = svg()
    print("mirror svg: %.2f KB, loop %gs" % (len(s.encode()) / 1024.0, T))
