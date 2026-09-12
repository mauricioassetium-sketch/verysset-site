# -*- coding: utf-8 -*-
"""Digital twin module (institutions.html, its own panel below the Trust Score card).

One inline SVG in the same flat geometry language as the home preloader (preloader.py):
a floor plate, five yellow verification points whose links draw into the asset, three
floating isometric layers (outline traces itself, then flat translucent facets fill) and a
crystal cap whose apex node keeps a soft idle blink. A scan plane rises through the stack
while it assembles. Styles live in assets/site.css under .tw-*.

Playback (assets/site.js): .tw-arm parks every animation at frame 0, .tw-play runs them once
when the module scrolls into view, .tw-off pauses the idle blink while it is off screen.
Without JS, or under prefers-reduced-motion, the markup already is the final composed twin.
Timeline: floor 0-0.8s, points 0.35-1.0s, links 0.55-1.95s, layers 1.0 / 1.55 / 2.1s,
cap 2.65s, apex node 3.3s, idle blink from 4.0s.
"""

CX = 280
HW, HH, T = 108, 43, 26
LAYERS = [324, 262, 200]                 # top face centre y, bottom to top
CAP_Y, CAP_APEX = 138, 50                # floating crystal cap: base diamond centre y, apex y
FLOOR = (84, 350, 280, 272, 476, 350, 280, 428)
# verification points and the twin vertex each one links into
NODES = [((84, 350), (172, 350)), ((476, 350), (388, 350)), ((280, 428), (280, 393)),
         ((58, 226), (172, 262)), ((502, 170), (388, 200))]
LEGEND = ["SPATIAL", "MATERIAL", "OPERATIONS", "VERIFIED"]   # same English as the preloader: keys reused


def _n(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def _iso(yc, hw=HW, hh=HH, t=T, cx=CX):
    lx, rx, by = cx - hw, cx + hw, yc + hh + t
    top = "%d,%d %d,%d %d,%d %d,%d" % (lx, yc, cx, yc - hh, rx, yc, cx, yc + hh)
    left = "%d,%d %d,%d %d,%d %d,%d" % (lx, yc, cx, yc + hh, cx, by, lx, yc + t)
    right = "%d,%d %d,%d %d,%d %d,%d" % (cx, yc + hh, rx, yc, rx, yc + t, cx, by)
    outline = ("M%d %dL%d %dL%d %dL%d %dZM%d %dV%dL%d %dL%d %dV%dM%d %dV%d"
               % (lx, yc, cx, yc - hh, rx, yc, cx, yc + hh, lx, yc, yc + t, cx, by, rx, yc + t, yc, cx, yc + hh, by))
    return top, left, right, outline


def twin_svg():
    o = ['<svg class="tw-svg" viewBox="0 0 560 440" fill="none" aria-hidden="true" focusable="false">']
    fl = "M%d %dL%d %dL%d %dL%d %dZ" % FLOOR
    grid = "".join("M%s %sL%s %sM%s %sL%s %s" % (
        _n(84 + 196 * f), _n(350 - 78 * f), _n(280 + 196 * f), _n(428 - 78 * f),
        _n(84 + 196 * f), _n(350 + 78 * f), _n(280 + 196 * f), _n(272 + 78 * f)) for f in (.25, .5, .75))
    o.append('<path class="tw-fade" d="%s" fill="#fff" fill-opacity=".035" style="animation-delay:.25s"/>' % fl)
    o.append('<path class="tw-fade" d="%s" stroke="#fff" stroke-opacity=".08" style="animation-delay:.45s"/>' % grid)
    o.append('<path class="tw-draw" pathLength="1" d="%s" stroke="#fff" stroke-opacity=".32"/>' % fl)
    # links from each verification point into the asset
    o.append('<g stroke="#FFD400" stroke-opacity=".5">' + "".join(
        '<path class="tw-draw" pathLength="1" d="M%d %dL%d %d" style="animation-delay:%.2fs"/>'
        % (x, y, tx, ty, .55 + i * .15) for i, ((x, y), (tx, ty)) in enumerate(NODES)) + '</g>')
    # scan plane rising through the stack while it assembles
    o.append('<path class="tw-scan" d="M152 350L280 299L408 350L280 401Z" stroke="#FFD400" fill="#FFD400" fill-opacity=".07"/>')
    # three layers, bottom to top: outline traces, then flat translucent facets fill
    for i, yc in enumerate(LAYERS):
        top, left, right, outline = _iso(yc)
        dl = 1.0 + i * .55
        o.append('<g class="tw-rise" style="animation-delay:%.2fs"><g class="tw-fade" style="animation-delay:%.2fs">'
                 '<polygon points="%s" fill="#FFD400" fill-opacity=".26"/>'
                 '<polygon points="%s" fill="#fff" fill-opacity=".1"/>'
                 '<polygon points="%s" fill="#FFD400" fill-opacity=".14"/></g>'
                 '<path class="tw-draw" pathLength="1" d="%s" stroke="#FFD400" stroke-width="1.6" style="animation-delay:%.2fs"/></g>'
                 % (dl, dl + .45, top, left, right, outline, dl))
    # crystal cap
    lx, rx, cy = CX - HW, CX + HW, CAP_Y
    o.append('<g class="tw-rise" style="animation-delay:2.65s"><g class="tw-fade" style="animation-delay:3.1s">'
             '<polygon points="%d,%d %d,%d %d,%d" fill="#fff" fill-opacity=".12"/>'
             '<polygon points="%d,%d %d,%d %d,%d" fill="#FFD400" fill-opacity=".3"/>'
             '<path d="M%d %dL%d %dL%d %d" stroke="#FFD400" stroke-opacity=".35" stroke-dasharray="3 4"/></g>'
             '<path class="tw-draw" pathLength="1" d="M%d %dL%d %dL%d %dL%d %dZM%d %dV%d" stroke="#FFD400" '
             'stroke-width="1.6" style="animation-delay:2.65s"/></g>'
             % (lx, cy, CX, cy + HH, CX, CAP_APEX, CX, cy + HH, rx, cy, CX, CAP_APEX,
                lx, cy, CX, cy - HH, rx, cy,
                lx, cy, CX, cy + HH, rx, cy, CX, CAP_APEX, CX, cy + HH, CAP_APEX))
    # verification points
    for i, ((x, y), _) in enumerate(NODES):
        dl = .35 + i * .15
        o.append('<g transform="translate(%d %d)"><circle class="tw-ring" r="5" stroke="#FFD400" stroke-width="1.4" '
                 'style="animation-delay:%.2fs"/><circle class="tw-pop" r="4.5" fill="#FFD400" style="animation-delay:%.2fs"/></g>'
                 % (x, y, dl, dl))
    # apex node: the composed, verified twin; blinks softly once assembled
    o.append('<g transform="translate(%d %d)"><circle class="tw-fade" r="11" stroke="#FFD400" stroke-opacity=".4" '
             'style="animation-delay:3.3s"/><circle class="tw-core" r="5.5" fill="#FFD400"/></g>' % (CX, CAP_APEX))
    o.append('</svg>')
    return "".join(o)


def module():
    leg = "".join('<li><span class="tw-n">%02d</span><span class="tw-l">%s</span></li>' % (i + 1, w)
                  for i, w in enumerate(LEGEND))
    return ('<figure class="tw rv" data-twin><figcaption class="tw-cp"><span class="eb">Digital twin</span>'
            '<h3 class="t3">Generated from verification, layer by layer.</h3>'
            '<ol class="tw-leg">%s</ol></figcaption><div class="tw-stage">%s</div></figure>' % (leg, twin_svg()))


if __name__ == "__main__":
    print("twin svg: %.2f KB, module: %.2f KB" % (len(twin_svg().encode()) / 1024.0, len(module().encode()) / 1024.0))
