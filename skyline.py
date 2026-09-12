# -*- coding: utf-8 -*-
"""Dubai skyline backdrop (compliance.html #jurisdiction, behind "Dubai incorporated").

One flat, grayscale inline SVG: a dotted far skyline, a mid layer of Dubai landmarks (Dubai
Frame, Emirates Towers, the DIFC Gate, Address Downtown, JW Marriott Marquis twins, Rose
Tower, a Marina cluster, Burj Al Arab), low podiums in front, and the Burj Khalifa on the
centre axis, drawn as its staggered spiralling setbacks and needle spire with one lighter
flat facet. Grays only (#d8dbe0 to #9aa0a8), no text, aria-hidden, pointer-events none.

viewBox 1600x400, preserveAspectRatio xMidYMax slice. CSS keeps the box at least 1:4 tall
(height max(210px, 25vw)), so the scale always follows the height: nothing is distorted, the
spire is never cropped, and narrow screens only trim the sides around the centred tower.
Styles: assets/site.css under .skysec / .sky.
"""

W, G = 1600, 400            # viewBox width, ground line y (viewBox height)
CX = 800                    # Burj Khalifa axis
C_FAR, C_DOT, C_MID, C_NEAR, C_BURJ, C_FACET = ("#d8dbe0", "#b3b8be", "#c3c7cd", "#b3b8be",
                                                "#9aa0a8", "#a9aeb5")


def _n(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def _poly(pts):
    return "M" + "L".join("%s %s" % (_n(x), _n(y)) for x, y in pts) + "Z"


def box(x, w, h):
    return "M%s %sV%sH%sV%sZ" % (_n(x), G, _n(G - h), _n(x + w), G)


def slant(x, w, h, rise, up_right=True):
    """roof sloping across the width"""
    lo, hi = G - h, G - h - rise
    return _poly([(x, G), (x, lo if up_right else hi), (x + w, hi if up_right else lo), (x + w, G)])


def emirates(x, w, h, rise, needle):
    """Emirates Towers / Address Downtown: sloped roof rising to a pointed crown"""
    return _poly([(x, G), (x, G - h), (x + w - 3, G - h - rise), (x + w - 1, G - h - rise - needle),
                  (x + w, G - h - rise), (x + w, G)])


def stepped(x, w, h, steps, spire=0):
    """symmetric setback crown; steps = [(inset from both sides, height), ...], optional needle"""
    left, right, y = [(x, G), (x, G - h)], [(x + w, G - h), (x + w, G)], G - h
    for inset, dh in steps:
        left += [(x + inset, y), (x + inset, y - dh)]
        right = [(x + w - inset, y - dh), (x + w - inset, y)] + right
        y -= dh
    top = []
    if spire:
        m = x + w / 2.0
        top = [(m - 1.2, y), (m - .5, y - spire), (m + .5, y - spire), (m + 1.2, y)]
    return _poly(left + top + right)


def twisted(x, w, h):
    """Cayan-like twisting tower, reduced to a flat wave"""
    return _poly([(x, G), (x + 4, G - h * .5), (x - 2, G - h), (x + w - 3, G - h), (x + w + 3, G - h * .5), (x + w, G)])


def sail(x, w, h):
    """Burj Al Arab: straight mast edge, bellied sail, crown spire and cantilevered helipad"""
    return ("M%s %sV%sQ%s %s %s %sZ" % (_n(x), G, _n(G - h), _n(x + w * 1.5), _n(G - h * .5), _n(x + w * .35), G)
            + box(x - 1.5, 3, h + 26)
            + "M%s %sH%sV%sH%sZ" % (_n(x - 16), _n(G - h * .78), _n(x + 1), _n(G - h * .78 + 4), _n(x - 16)))


def hollow(x, w, h, ox, ow, oy0, oy1):
    """outer block with a see-through opening (evenodd): Dubai Frame, DIFC Gate"""
    return box(x, w, h) + "M%s %sV%sH%sV%sZ" % (_n(x + ox), _n(G - oy0), _n(G - oy1), _n(x + ox + ow), _n(G - oy0))


# Burj Khalifa profile, ground up: (top height, left half width, right half width). Left and right
# setbacks land at different heights, which is what reads as the spiralling Y plan in elevation.
BURJ_BODY = [(60, 30, 28), (100, 30, 23), (136, 25, 23), (168, 25, 18.5), (196, 20.5, 18.5), (220, 20.5, 14),
             (240, 16, 14), (256, 16, 10.5), (268, 11.5, 10.5), (278, 11.5, 7.5)]
BURJ_SPIRE = [(292, 6.5, 6.5), (306, 5, 5), (320, 3.8, 3.8), (334, 2.8, 2.8)]
BURJ_TIP = 392


def burj():
    segs, lo = [], 0
    for hi, l, r in BURJ_BODY + BURJ_SPIRE:
        segs.append((lo, hi, l, r))
        lo = hi
    left = []
    for lo, hi, l, r in segs:
        left += [(CX - l, G - lo), (CX - l, G - hi)]
    right = []
    for lo, hi, l, r in reversed(segs):
        right += [(CX + r, G - hi), (CX + r, G - lo)]
    top = lo
    needle_l = [(CX - 2, G - top), (CX - .5, G - BURJ_TIP)]
    needle_r = [(CX + .5, G - BURJ_TIP), (CX + 2, G - top)]
    outline = _poly(left + needle_l + needle_r + right)
    facet = _poly([(CX, G), (CX, G - BURJ_TIP)] + needle_r + right)
    return outline, facet


def far_layer():
    seed = [20260913]

    def rnd():
        seed[0] = (seed[0] * 1103515245 + 12345) & 0x7fffffff
        return seed[0] / float(0x7fffffff)

    d, x = [], -12.0
    while x < W + 12:
        w = 16 + rnd() * 26
        h = 50 + rnd() * 100
        k = rnd()
        if k < .2:
            d.append(slant(x, w, h, 8 + rnd() * 14, rnd() < .5))
        elif k < .38:
            d.append(stepped(x, w, h, [(w * .18, 8 + rnd() * 10)], spire=(12 + rnd() * 18) if rnd() < .5 else 0))
        else:
            d.append(box(x, w, h))
        x += w * (.6 + rnd() * .55)
    return "".join(d)


def mid_layer():
    solid = "".join([
        box(0, 36, 96), stepped(40, 30, 150, [(5, 14), (10, 10)], 18),
        box(205, 26, 118), slant(236, 30, 150, 16), stepped(300, 34, 176, [(6, 16), (12, 12)], 26),
        twisted(360, 26, 160), box(398, 40, 104),
        emirates(450, 34, 200, 26, 22), emirates(494, 30, 170, 22, 16),          # Emirates Towers
        box(624, 30, 132), stepped(660, 36, 158, [(6, 14)]), box(704, 40, 90),
        emirates(846, 34, 186, 30, 12), box(890, 40, 120),                        # Address Downtown
        stepped(944, 34, 206, [(4, 12), (9, 10), (13, 8)]),                       # JW Marriott Marquis
        stepped(984, 34, 206, [(4, 12), (9, 10), (13, 8)]),
        stepped(1036, 30, 150, [(5, 14)], 20), stepped(1080, 26, 196, [(3, 18), (7, 14)], 34),   # Rose Tower
        box(1116, 38, 128), twisted(1170, 28, 178), stepped(1206, 32, 222, [(4, 14), (9, 12)], 38),
        box(1246, 30, 170), slant(1280, 34, 150, 18, False), stepped(1322, 30, 188, [(5, 16)], 16),
        box(1360, 44, 96), sail(1440, 70, 168), box(1560, 40, 84),               # Burj Al Arab
    ])
    see_through = (hollow(118, 62, 128, 12, 38, 12, 114)                         # Dubai Frame
                   + hollow(540, 76, 98, 22, 32, 0, 60))                         # DIFC Gate
    return solid, see_through


def near_layer():
    return "".join(box(x, w, h) for x, w, h in [
        (0, 110, 34), (96, 60, 22), (180, 90, 40), (290, 70, 28), (380, 100, 46), (500, 80, 30), (610, 100, 38),
        (690, 60, 24), (850, 70, 24), (930, 90, 36), (1030, 70, 26), (1110, 110, 44), (1230, 80, 30),
        (1320, 90, 40), (1420, 60, 20), (1500, 100, 34), (0, W, 6)])


def svg():
    outline, facet = burj()
    solid, see_through = mid_layer()
    return ('<svg class="sky" viewBox="0 0 1600 400" preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">'
            '<defs><pattern id="vsky-dot" width="7" height="7" patternUnits="userSpaceOnUse">'
            '<circle cx="3.5" cy="3.5" r=".9" fill="%s"/></pattern><path id="vsky-far" d="%s"/></defs>'
            '<use href="#vsky-far" fill="%s"/><use href="#vsky-far" fill="url(#vsky-dot)"/>'
            '<path fill="%s" d="%s"/><path fill="%s" fill-rule="evenodd" d="%s"/>'
            '<path fill="%s" d="%s"/><path fill="%s" d="%s"/>'
            '<path fill="%s" d="%s"/></svg>'
            % (C_DOT, far_layer(), C_FAR, C_MID, solid, C_MID, see_through,
               C_BURJ, outline, C_FACET, facet, C_NEAR, near_layer()))


if __name__ == "__main__":
    print("skyline svg: %.2f KB" % (len(svg().encode()) / 1024.0))
