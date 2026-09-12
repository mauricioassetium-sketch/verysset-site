# -*- coding: utf-8 -*-
"""Satellite verification preloader (index.html only).

One inline SVG scene, CSS keyframes only (styles live in assets/site.css under .vpl-*).
The tiny inline script right after the overlay decides, before first paint, whether the
overlay plays: it is removed at once when this browser session already saw it
(sessionStorage "vs-preloader-played") or when prefers-reduced-motion is set.
Visible words are plain SVG <text>, so build.py's i18nize() keys them automatically.
Timeline (8s intro): beat 1 earth + satellite 0.0-2.0s, beat 2 scan + trust score 2.0-4.8s
(a 6px yellow underline sweeps in under the locked score at 4.8s), beat 3 twin + chips 4.8-7.0s,
beat 4 hold to 7.7s. Exit: at 7.7s the score underline lifts off the counter and stretches into
the 6px curtain edge bar (.vpl-bar: a FLIP from the underline's measured rect to full width on the
overlay's bottom edge, 0.5s); from 8.0s the overlay rises bottom to top carrying that bar
(translateY(-100%), 1.3s) and is removed. Waits at most 150ms for window load, so it is gone by ~9.5s.
"""

# ground verification points: (x, y, delay seconds), synced to the linear beam sweep
PTS = [(140, 344, 2.17), (225, 337, 2.86), (310, 334, 3.46), (395, 335, 4.09), (470, 338, 4.71)]

# tiny flat glyphs drawn under each point (satellite, IoT, LiDAR, drone, IR)
GLYPHS = [
    "M-6 0h3M3 0h3M-2-3h4v6h-4z",                       # satellite
    "M-4-1a5 5 0 0 1 8 0M-2 1a2.5 2.5 0 0 1 4 0",       # IoT waves
    "M0-4v8M-4 3l4-7 4 7",                              # LiDAR fan
    "M-5-4l10 8M5-4l-10 8M-5-4h0M5 4h0",                # drone cross
    "M-5 0q2.5-4 5 0t5 0M-5 3q2.5-4 5 0t5 0",           # IR heat wave
]

# score underline (x, y, w, h), the "93" advance box; the curtain bar starts from this exact rect
UL = (573, 115, 87, 6)

COUNTS = [("0", 0.0), ("12", 2.17), ("34", 2.86), ("58", 3.46), ("79", 4.09), ("93", 4.71)]


def _iso(yc, hw=75, hh=30, t=22, cx=305):
    top = "%d,%d %d,%d %d,%d %d,%d" % (cx - hw, yc, cx, yc - hh, cx + hw, yc, cx, yc + hh)
    left = "%d,%d %d,%d %d,%d %d,%d" % (cx - hw, yc, cx, yc + hh, cx, yc + hh + t, cx - hw, yc + t)
    right = "%d,%d %d,%d %d,%d %d,%d" % (cx, yc + hh, cx + hw, yc, cx + hw, yc + t, cx, yc + hh + t)
    outline = ("M%d %dL%d %dL%d %dL%d %dZM%d %dV%dL%d %dL%d %dV%dM%d %dV%d"
               % (cx - hw, yc, cx, yc - hh, cx + hw, yc, cx, yc + hh,
                  cx - hw, yc, yc + t, cx, yc + hh + t, cx + hw, yc + t, yc, cx, yc + hh, yc + hh + t))
    return top, left, right, outline


def preloader():
    o = []
    o.append('<div id="vs-preloader" class="vpl" aria-hidden="true">'
             '<svg class="vpl-svg" viewBox="0 0 680 440" role="presentation" focusable="false">'
             '<defs><clipPath id="vplc"><circle cx="340" cy="2320" r="2000"/></clipPath></defs>')
    # stars
    o.append('<g class="vpl-stars" fill="#fff">' + "".join(
        '<circle cx="%d" cy="%d" r="%s"/>' % (x, y, r) for x, y, r in
        [(60, 40, 1), (120, 210, .8), (430, 30, .8), (560, 190, 1), (640, 250, .8), (30, 120, .8), (470, 150, .7)]) + '</g>')
    # beat 1: earth horizon + grid
    o.append('<g class="vpl-earth"><circle cx="340" cy="2320" r="2000" fill="#16202b"/>'
             '<g clip-path="url(#vplc)" fill="none" stroke="#223140" stroke-width="1">'
             '<circle cx="340" cy="2320" r="1975"/><circle cx="340" cy="2320" r="1940"/><circle cx="340" cy="2320" r="1895"/>'
             + "".join('<path d="M%d 318L%d 440"/>' % (x, 340 + (x - 340) * 0.86) for x in range(20, 700, 80)) +
             '</g><circle cx="340" cy="2320" r="2000" fill="none" stroke="#2e4254" stroke-width="1.5"/></g>')
    # orbit
    o.append('<path class="vpl-orbit" d="M-60 150Q300 5 740 150" fill="none" stroke="#FFD400" '
             'stroke-width="1.5" stroke-linecap="round" stroke-dasharray="1 8"/>')
    # beat 2: scan beam (apex at the satellite, rotated about it)
    o.append('<polygon class="vpl-beam" points="300,92 270,352 330,352" fill="#FFD400"/>')
    # ground points
    for i, (x, y, dl) in enumerate(PTS):
        o.append('<g transform="translate(%d %d)">'
                 '<path d="%s" transform="translate(0 16)" fill="none" stroke="#5f7082" stroke-width="1.2" stroke-linecap="round"/>'
                 '<circle r="4" fill="#2c3b4a"/>'
                 '<circle class="vpl-lit" r="4" fill="#FFD400" style="animation-delay:%.2fs"/>'
                 '<circle class="vpl-ring" r="4" fill="none" stroke="#FFD400" stroke-width="1.5" style="animation-delay:%.2fs"/>'
                 '</g>' % (x, y, GLYPHS[i], dl, dl))
    # beat 3: links from points to the twin base
    o.append('<g class="vpl-links" stroke="#FFD400" stroke-width="1" fill="none">' + "".join(
        '<path pathLength="1" d="M%d %dL305 318" style="animation-delay:%.2fs"/>' % (x, y, 4.8 + i * 0.1)
        for i, (x, y, _) in enumerate(PTS)) + '</g>')
    # digital twin: 3 stacked isometric layers, outline draws then facets fill
    labels = [("1", "SPATIAL"), ("2", "MATERIAL"), ("3", "OPERATIONS")]
    for i, yc in enumerate([262, 214, 166]):
        top, left, right, outline = _iso(yc)
        dl = 4.8 + i * 0.32
        o.append('<g class="vpl-layer" style="animation-delay:%.2fs">'
                 '<g class="vpl-fac" style="animation-delay:%.2fs">'
                 '<polygon points="%s" fill="#FFD400" fill-opacity=".26"/>'
                 '<polygon points="%s" fill="#FFFFFF" fill-opacity=".10"/>'
                 '<polygon points="%s" fill="#FFD400" fill-opacity=".14"/></g>'
                 '<path class="vpl-draw" pathLength="1" d="%s" fill="none" stroke="#FFD400" stroke-width="1.6" '
                 'stroke-linejoin="round" style="animation-delay:%.2fs"/>'
                 '<path d="M226 %dH204" stroke="#FFD400" stroke-opacity=".5"/>'
                 '<text class="vpl-lab" x="198" y="%d" text-anchor="end">'
                 '<tspan class="vpl-y">%s</tspan> <tspan>%s</tspan></text></g>'
                 % (dl, dl + 0.6, top, left, right, outline, dl, yc + 11, yc + 15, labels[i][0], labels[i][1]))
    # beat 1: satellite (outer g = final position, inner g = CSS motion)
    o.append('<g transform="translate(300 80)"><g class="vpl-sat">'
             '<rect x="-38" y="-5" width="26" height="10" fill="#0A0A09" stroke="#FFD400" stroke-width="1.5"/>'
             '<rect x="12" y="-5" width="26" height="10" fill="#0A0A09" stroke="#FFD400" stroke-width="1.5"/>'
             '<path d="M-29-5v10M-20-5v10M21-5v10M30-5v10M-12 0h4M8 0h4" stroke="#FFD400" stroke-width="1"/>'
             '<rect x="-8" y="-9" width="16" height="18" rx="1" fill="#fff"/>'
             '<rect x="-8" y="3" width="16" height="3" fill="#E6BF00"/>'
             '<rect x="-3" y="9" width="6" height="4" fill="#FFD400"/></g></g>')
    # trust score counter, top right
    o.append('<g class="vpl-score"><text class="vpl-cap" x="660" y="42" text-anchor="end">TRUST SCORE</text>')
    for n, (num, dl) in enumerate(COUNTS):
        last = n == len(COUNTS) - 1
        if n == 0:
            anim = 'animation:vpl-hide 1ms linear %.2fs forwards' % COUNTS[1][1]
        elif last:
            anim = 'animation:vpl-show 1ms linear %.2fs both' % dl
        else:
            anim = ('animation:vpl-show 1ms linear %.2fs both,vpl-hide 1ms linear %.2fs forwards'
                    % (dl, COUNTS[n + 1][1]))
        o.append('<text class="vpl-num" x="660" y="104" text-anchor="end" style="%s">%s</text>' % (anim, num))
    o.append('<rect class="vpl-ul" x="%d" y="%d" width="%d" height="%d" fill="#FFD400"/>' % UL)
    o.append('<g class="vpl-ok"><path d="M648 141l5 5 8-10" fill="none" stroke="#FFD400" stroke-width="2.2" '
             'stroke-linecap="round" stroke-linejoin="round"/>'
             '<text class="vpl-cap vpl-y" x="640" y="146" text-anchor="end">VERIFIED</text></g></g>')
    # chips
    o.append('<g class="vpl-chip vpl-c1"><rect x="96" y="392" width="228" height="28" rx="14" fill="#0A0A09" '
             'stroke="#FFD400" stroke-opacity=".6"/><text class="vpl-mono" x="210" y="410" text-anchor="middle" '
             'data-noi18n>SHA-256 · 9f2a…c1de</text></g>')
    o.append('<g class="vpl-chip vpl-c2"><rect x="340" y="392" width="244" height="28" rx="14" fill="#FFD400"/>'
             '<text class="vpl-cap vpl-dk" x="462" y="410" text-anchor="middle">REGISTERED ON DLT</text></g>')
    o.append('</svg><i class="vpl-bar"></i></div>')
    o.append("<script>(function(){var d=document,h=d.documentElement,e=d.getElementById('vs-preloader'),"
             "k='vs-preloader-played',s=null,w=window;"
             "try{s=w.sessionStorage.getItem(k);w.sessionStorage.setItem(k,'1')}catch(x){}"
             "if(s||(w.matchMedia&&w.matchMedia('(prefers-reduced-motion: reduce)').matches)){e.parentNode.removeChild(e);return}"
             "h.classList.add('vpl-lock');var gone=0;"
             "function out(){if(gone)return;gone=1;"
             # FLIP: park the 6px bar exactly on the score underline, CSS then carries it to the bottom edge
             "try{var u=e.querySelector('.vpl-ul').getBoundingClientRect(),W=e.clientWidth,H=e.clientHeight,st=e.style;"
             "if(u.width&&W){st.setProperty('--bx',u.left+'px');st.setProperty('--by',(u.top-H+6)+'px');"
             "st.setProperty('--sx',u.width/W);st.setProperty('--sy',u.height/6);e.querySelector('.vpl-bar').offsetWidth}}catch(x){}"
             "e.classList.add('vpl-out');"
             "setTimeout(function(){if(e.parentNode)e.parentNode.removeChild(e);h.classList.remove('vpl-lock')},1640)}"
             "setTimeout(function(){if(d.readyState==='complete')out();else{w.addEventListener('load',out);setTimeout(out,150)}},7700)"
             "})();</script>")
    return "".join(o)


if __name__ == "__main__":
    s = preloader()
    print("preloader: %.1f KB" % (len(s.encode("utf-8")) / 1024.0))
