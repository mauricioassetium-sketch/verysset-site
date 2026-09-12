#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verysset planet map generator.

Builds a LIGHTWEIGHT dotted (halftone) world map as pure inline SVG:
  * no external tiles, no map library, no fonts
  * coarse continent polygons (hand authored, ~2.5 degree fidelity) are
    rasterised onto an equirectangular dot lattice
  * the whole land field is emitted as ONE <path> of tiny relative squares,
    which keeps the byte cost near 12 characters per dot
  * a second path carries the "hot" dots inside each verification cell, so the
    regions around the marker nodes glow yellow for free

Projection: plain equirectangular, clipped to lat +84 .. -58 (Antarctica is
dropped so the aspect ratio stays wide and institutional).
    x = (lon + 180) * SX          SX = 1.6 units / degree   -> 576 units wide
    y = (84 - lat)  * SX                                    -> 227.2 -> 228 tall
Lattice: 2.5 degrees => 4 units. Dot square = 2 units (50% duty cycle).
"""

VB_W, VB_H = 576, 228
SX = 1.6                 # units per degree
LAT_TOP, LAT_BOT = 84.0, -58.0
STEP_DEG = 2.5
CELL = 4                 # lattice pitch in user units
DOT = 2                  # dot square side in user units
COLS = VB_W // CELL      # 144
ROWS = VB_H // CELL      # 57


def px(lon):
    return (lon + 180.0) * SX


def py(lat):
    return (LAT_TOP - lat) * SX


# ---------------------------------------------------------------------------
# coarse land polygons, (lon, lat).  Traced to roughly 3 degree fidelity: at a
# 2.5 degree lattice nothing finer than that survives rasterisation anyway.
# ---------------------------------------------------------------------------
LAND = {
"north_america": [
 (-168.0,65.7),(-164.5,68.8),(-156.5,71.4),(-148.0,70.4),(-140.0,69.6),
 (-132.0,69.5),(-124.0,70.2),(-114.0,68.9),(-105.0,68.8),(-96.0,68.3),
 (-88.0,70.5),(-82.0,73.4),(-74.0,76.2),(-67.0,70.0),(-63.5,60.5),
 (-57.5,54.0),(-61.0,47.6),(-66.5,44.6),(-70.5,42.5),(-74.5,39.6),
 (-76.0,35.2),(-81.2,31.2),(-80.2,25.2),(-82.8,29.0),(-85.0,29.8),
 (-89.0,29.1),(-94.0,29.6),(-97.5,26.0),(-95.5,18.6),(-92.0,18.4),
 (-87.0,21.5),(-87.8,17.4),(-83.2,15.0),(-79.0,9.2),(-77.4,8.0),
 (-82.5,8.6),(-85.8,11.0),(-91.0,14.0),(-96.0,15.7),(-105.0,20.5),
 (-110.0,24.2),(-114.5,31.2),(-118.2,34.0),(-122.0,37.0),(-124.5,43.0),
 (-124.5,48.4),(-130.5,54.5),(-137.5,59.0),(-145.0,60.1),(-152.0,59.2),
 (-158.5,56.0),(-162.5,58.5),(-165.5,60.6),(-161.5,64.2),
],
"greenland": [
 (-45.0,83.2),(-30.0,83.0),(-21.5,76.5),(-20.0,70.0),(-24.0,66.0),
 (-32.0,61.0),(-42.5,60.2),(-50.0,62.5),(-54.0,67.0),(-58.5,72.0),
 (-62.5,76.0),(-56.0,80.0),(-50.0,82.2),
],
"south_america": [
 (-80.8,-4.0),(-79.5,2.0),(-77.0,8.0),(-71.5,11.5),(-66.0,10.6),
 (-60.0,9.0),(-52.0,5.0),(-50.0,0.0),(-44.0,-2.0),(-38.0,-5.0),
 (-35.2,-8.0),(-37.5,-13.0),(-39.0,-18.0),(-43.0,-23.0),(-48.5,-25.5),
 (-53.5,-34.0),(-57.5,-38.5),(-62.0,-39.0),(-63.0,-42.0),(-65.5,-45.0),
 (-68.5,-50.5),(-69.5,-52.5),(-74.5,-53.0),(-75.0,-49.0),(-73.5,-44.0),
 (-73.5,-37.0),(-71.5,-30.0),(-70.5,-23.0),(-70.5,-18.0),(-75.0,-14.5),
 (-79.0,-7.0),
],
"africa": [
 (-17.0,14.8),(-16.5,20.0),(-13.0,27.5),(-8.5,33.0),(-5.5,35.9),
 (1.0,36.6),(9.5,37.3),(11.5,33.5),(20.0,32.0),(25.0,31.6),
 (32.5,31.2),(34.5,28.0),(35.5,23.5),(38.0,18.0),(39.5,15.0),
 (43.5,12.5),(44.0,10.4),(51.5,11.8),(48.0,4.0),(42.0,-1.0),
 (40.5,-10.5),(37.0,-17.0),(35.5,-24.0),(32.5,-28.5),(27.0,-33.7),
 (19.5,-34.8),(15.0,-27.5),(13.5,-22.0),(11.5,-16.0),(9.0,-1.5),
 (8.5,4.5),(3.0,6.4),(-4.0,5.2),(-8.0,4.5),(-13.5,8.5),(-16.5,12.0),
],
"eurasia": [
 (-9.5,36.9),(-9.0,39.5),(-8.9,43.3),(-4.5,43.5),(-1.5,43.4),
 (-1.2,46.2),(-2.5,47.3),(-4.8,48.5),(-1.5,49.6),(2.0,51.0),
 (4.3,52.0),(7.0,53.5),(8.2,54.5),(8.1,57.1),(10.6,57.7),
 (12.6,56.1),(14.5,55.4),(18.9,54.6),(21.0,56.0),(24.0,57.6),
 (28.0,59.4),(30.3,59.9),(27.0,63.0),(22.5,65.8),(21.5,68.4),
 (18.0,69.6),(24.0,70.9),(28.5,71.1),(33.0,69.8),(38.5,66.2),
 (41.0,66.0),(44.5,67.9),(52.0,68.6),(58.0,68.8),(66.0,68.0),
 (69.5,73.0),(74.0,72.5),(77.0,72.0),(80.0,73.6),(86.0,76.0),
 (96.0,77.0),(104.0,76.5),(110.0,74.0),(114.0,73.5),(122.0,73.5),
 (129.0,73.0),(136.0,72.0),(142.0,72.5),(148.0,70.0),(155.0,71.0),
 (162.0,70.0),(170.0,69.8),(180.0,68.5),(180.0,64.5),(172.0,60.0),
 (163.0,58.0),(162.0,54.5),(156.5,51.5),(158.0,53.5),(154.0,47.5),
 (142.5,46.0),(140.5,45.5),(135.0,43.0),(130.5,42.5),(127.5,39.5),
 (125.5,39.5),(122.0,39.5),(118.5,38.5),(121.0,32.0),(119.0,26.0),
 (114.0,22.5),(110.0,21.5),(108.5,21.0),(109.5,11.0),(105.0,9.0),
 (103.6,1.4),(100.5,6.5),(98.5,8.5),(97.5,16.5),(94.5,16.0),
 (90.5,22.0),(88.0,21.5),(86.5,20.8),(80.5,15.5),(80.2,13.0),
 (79.9,9.5),(77.0,8.2),(75.0,13.0),(72.8,19.0),(69.0,22.5),
 (67.0,24.5),(62.0,25.2),(57.5,25.4),(54.0,26.8),(50.0,29.8),
 (48.5,30.0),(50.5,27.5),(52.5,24.5),(55.5,24.0),(57.8,22.0),
 (59.8,22.5),(57.5,18.5),(54.0,17.0),(52.0,15.5),(48.0,14.0),
 (44.5,12.8),(43.2,16.5),(41.5,18.5),(39.0,21.5),(37.0,24.5),
 (35.0,28.0),(34.3,31.2),(35.6,34.5),(36.0,36.2),(33.0,36.0),
 (30.5,36.3),(28.0,36.8),(26.5,38.5),(23.5,40.0),(23.0,37.0),
 (21.5,39.0),(19.3,40.2),(18.5,42.5),(13.5,45.5),(15.0,42.0),
 (16.2,38.9),(15.6,38.0),(16.1,39.6),(14.0,40.8),(12.0,41.5),
 (10.5,43.0),(10.2,44.0),(8.5,44.4),(7.5,43.8),(3.0,43.2),
 (3.2,42.4),(0.8,40.5),(0.0,39.5),(-0.8,37.8),(-2.2,36.7),
 (-5.3,36.1),(-7.4,37.2),
],
"australia": [
 (113.2,-22.0),(114.0,-26.0),(115.0,-31.5),(118.0,-34.5),(124.0,-33.5),
 (129.0,-32.0),(134.0,-33.0),(136.5,-35.2),(138.5,-35.0),(140.5,-38.0),
 (145.0,-38.5),(148.5,-37.6),(150.5,-35.0),(153.5,-30.0),(153.0,-25.0),
 (148.0,-20.0),(146.0,-19.0),(142.5,-11.0),(137.0,-12.2),(132.5,-11.0),
 (130.0,-12.5),(127.0,-14.0),(122.0,-17.0),(117.0,-20.5),
],
"tasmania": [(145.0,-40.8),(148.3,-40.8),(148.0,-43.5),(145.2,-43.5)],
"nz_north": [(172.8,-34.5),(176.0,-37.0),(178.5,-37.8),(175.0,-41.4),(172.6,-39.0)],
"nz_south": [(166.8,-45.8),(170.5,-42.5),(174.2,-41.3),(171.5,-46.6),(168.0,-46.8)],
"honshu":   [(139.5,34.6),(141.0,38.2),(141.5,41.3),(139.8,40.5),(137.5,37.2),(135.8,35.6),(135.0,33.6),(138.5,34.0)],
"hokkaido": [(141.0,41.8),(145.3,43.3),(145.2,44.8),(141.5,45.4),(140.4,43.2)],
"kyushu":   [(129.8,32.8),(131.8,33.6),(131.6,31.4),(130.2,31.0)],
"uk":       [(-5.2,50.1),(-3.0,50.7),(1.6,51.3),(0.0,53.5),(-1.0,54.6),(-2.2,56.0),(-4.0,58.6),(-5.6,57.2),(-6.2,55.4),(-4.8,53.4),(-4.5,52.2),(-5.0,51.2)],
"ireland":  [(-10.2,51.6),(-6.0,52.2),(-6.2,54.6),(-8.0,55.3),(-10.0,54.0)],
"iceland":  [(-24.3,65.0),(-18.0,66.5),(-14.0,65.6),(-16.5,63.8),(-22.0,63.9)],
"madagascar":[(49.5,-13.0),(50.5,-16.0),(48.5,-21.0),(47.0,-25.2),(44.0,-25.0),(43.2,-21.0),(44.5,-16.0),(46.5,-14.0)],
"sri_lanka":[(79.8,9.6),(81.9,8.0),(81.5,6.0),(80.0,6.0),(79.6,8.6)],
"sumatra":  [(95.2,5.6),(98.5,3.5),(101.5,-0.5),(104.5,-2.0),(106.0,-5.9),(103.0,-5.4),(100.0,0.0),(96.0,3.0)],
"java":     [(105.2,-6.0),(110.0,-6.6),(114.4,-8.0),(114.5,-8.8),(108.0,-7.9),(105.5,-7.2)],
"borneo":   [(109.0,1.8),(113.0,4.2),(117.2,6.4),(119.0,4.4),(118.0,1.0),(116.5,-3.5),(112.0,-3.4),(110.0,-1.0)],
"sulawesi": [(119.8,1.2),(125.2,1.6),(125.0,-2.0),(123.0,-5.4),(119.5,-3.4),(118.8,0.0)],
"new_guinea":[(131.0,-1.0),(136.0,-2.2),(141.0,-2.8),(146.0,-5.2),(150.8,-6.4),(147.0,-9.2),(143.0,-9.2),(138.0,-8.4),(134.0,-4.2),(131.2,-3.2)],
"luzon":    [(119.8,14.4),(122.2,16.2),(122.0,18.5),(120.0,18.4),(119.5,15.0)],
"mindanao": [(121.8,6.2),(126.4,7.0),(126.2,9.4),(122.6,9.6)],
"cuba":     [(-84.9,22.0),(-80.0,23.2),(-74.8,20.4),(-78.0,19.9),(-83.0,21.4)],
"hispaniola":[(-74.4,19.8),(-68.4,19.6),(-68.6,18.2),(-72.5,17.8)],
"taiwan":   [(120.2,23.0),(122.0,25.2),(121.5,22.0),(120.0,22.6)],
"sakhalin": [(142.0,46.2),(143.3,50.0),(143.0,54.3),(141.6,52.0),(141.5,47.6)],
"svalbard": [(10.5,77.8),(20.0,79.2),(28.0,80.2),(15.0,80.6),(10.0,79.4)],
"novaya":   [(52.5,70.8),(58.0,73.2),(68.5,76.5),(62.0,76.6),(55.0,73.0)],
"newfoundland":[(-59.3,47.6),(-52.8,47.4),(-55.5,51.5),(-58.8,50.2)],
"baffin":   [(-78.0,67.0),(-71.0,70.5),(-63.0,66.0),(-68.0,63.0),(-75.0,63.5)],
"victoria": [(-118.0,71.0),(-105.0,72.5),(-100.0,69.5),(-114.0,68.8)],
"ellesmere":[(-85.0,79.0),(-70.0,82.5),(-62.0,81.0),(-78.0,76.5)],
"cyprus":   [(32.3,35.6),(34.5,35.7),(33.8,34.6),(32.4,34.7)],
"sicily":   [(12.4,38.0),(15.6,38.3),(15.1,36.7),(12.6,37.5)],
"sardinia": [(8.2,41.2),(9.8,41.2),(9.5,38.9),(8.4,39.2)],
"timor":    [(124.0,-8.4),(127.3,-8.4),(125.5,-9.6),(124.0,-9.3)],
"hainan":   [(108.6,20.1),(111.0,19.9),(110.4,18.2),(108.7,18.6)],
"jamaica":  [(-78.4,18.5),(-76.2,18.5),(-76.3,17.7),(-78.3,17.8)],
}

# subtracted water bodies (holes inside the traced outlines)
HOLES = {
"hudson_bay":  [(-95.0,58.0),(-85.0,55.2),(-77.5,56.5),(-76.0,62.5),(-82.0,64.5),(-90.0,64.0),(-95.5,60.0)],
"black_sea":   [(28.5,41.2),(33.0,42.0),(38.0,43.6),(40.5,43.2),(37.0,46.6),(31.0,46.4),(29.2,45.0),(28.2,42.2)],
"caspian_sea": [(47.5,37.6),(53.5,38.4),(53.2,42.4),(51.0,45.6),(48.2,46.0),(47.0,43.0),(49.0,40.0)],
"baltic_sea":  [(13.0,54.4),(20.0,55.0),(21.0,58.5),(18.0,61.5),(21.5,64.5),(19.0,64.0),(17.5,60.0),(14.0,55.8)],
"great_lakes": [(-92.0,47.5),(-84.0,49.0),(-76.5,44.5),(-83.0,41.4),(-88.0,42.0)],
"gulf_calif":  [(-114.5,31.5),(-112.0,29.0),(-108.0,25.0),(-110.5,24.5),(-113.0,28.0)],
"red_sea":     [(34.5,28.2),(39.0,21.0),(43.0,13.2),(41.0,13.0),(36.6,21.5),(33.4,27.6)],
"persian_gulf":[(48.6,30.2),(52.0,27.0),(56.5,25.2),(55.0,23.6),(50.6,27.0),(47.6,29.6)],
}


def inside(poly, x, y):
    """ray casting point in polygon"""
    n = len(poly)
    c = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            c = not c
        j = i
    return c


def is_land(lon, lat):
    for poly in LAND.values():
        if inside(poly, lon, lat):
            for h in HOLES.values():
                if inside(h, lon, lat):
                    return False
            return True
    return False


# ---------------------------------------------------------------------------
# verification nodes:  lon, lat, asset type, place, detail, counter step,
#                      sensor flag, label side, vertical nudge (user units)
# ---------------------------------------------------------------------------
NODES = [
    (  55.27,  25.20, "Real Estate",        "Dubai, UAE",               "DIFC tower portfolio",   19, 1, "r",   0),
    ( -60.00,  -3.10, "Carbon Bonds",       "Amazon, Brazil",           "Verified forest lots",   23, 1, "r",   0),
    (  28.04, -26.20, "Gold Mining",        "Gauteng, South Africa",    "Proof of reserves",      14, 0, "r",   0),
    (   7.00,  51.40, "Industrial Plants",  "Ruhr, Germany",            "Plant integrity",        11, 1, "r",  10),
    (   5.30,  60.40, "Offshore Energy",    "Bergen, Norway",           "Platform and grid",       9, 0, "l",  -8),
    ( -61.00, -33.50, "Agriculture",        "Pampas, Argentina",        "Harvest provenance",     17, 0, "r",   4),
    ( 103.80,   1.35, "Ports &amp; Logistics", "Singapore",             "Cargo chain of custody", 21, 1, "r",   0),
    ( -68.20, -23.50, "Lithium &amp; Water",   "Atacama, Chile",        "Brine and water rights", 12, 0, "l",  -2),
    ( 106.90,  47.90, "Rare Earths",        "Gobi, Mongolia",           "Extraction lineage",      8, 1, "r",   0),
    (-122.00,  53.50, "Timber",             "British Columbia, Canada", "Chain of custody",       13, 0, "r",   0),
    (  44.00,  24.70, "Solar Farms",        "Riyadh, Saudi Arabia",     "Output attestation",     10, 0, "l",  12),
    (  -6.26,  53.35, "Data Centers",       "Dublin, Ireland",          "Uptime and power draw",   7, 1, "l",  10),
]

ORBIT = "M-40 52 C 150 0 430 0 616 52"
HOT_R = 13.0            # user units: dots inside this radius of a node glow


def dot_paths():
    """Rasterise the land mask onto the lattice. Returns (land_d, hot_d, counts)."""
    nx = [px(n[0]) for n in NODES]
    ny = [py(n[1]) for n in NODES]
    land, hot = [], []
    for j in range(ROWS):
        cy = 4 * j + 1
        lat = LAT_TOP - (cy / SX)
        if lat > LAT_TOP or lat < LAT_BOT:
            continue
        for k in range(COLS):
            cx = 4 * k + 1
            lon = (cx / SX) - 180.0
            if not is_land(lon, lat):
                continue
            h = False
            for i in range(len(nx)):
                dx, dy = cx - nx[i], cy - ny[i]
                if dx * dx + dy * dy <= HOT_R * HOT_R:
                    h = True
                    break
            (hot if h else land).append((4 * k, 4 * j))
    return _pack(land), _pack(hot), (len(land), len(hot))


def _pack(cells):
    """One path, relative moves, tiny squares. ~12 bytes per dot."""
    out = []
    cxp = cyp = None
    for (x, y) in cells:
        if cxp is None:
            out.append("M%d %d" % (x, y))
        else:
            dx, dy = x - cxp, y - cyp
            if dy == 0:
                out.append("m%d 0" % dx)
            elif dx == 0:
                out.append("m0 %d" % dy)
            else:
                out.append("m%d %d" % (dx, dy))
        out.append("h%dv%dh-%dz" % (DOT, DOT, DOT))
        cxp, cyp = x, y
    return "".join(out)


def graticule():
    o = []
    for lon in range(-150, 180, 30):
        o.append("M%.0f 0V%d" % (px(lon), VB_H))
    for lat in (60, 30, -30):
        o.append("M0 %.0fH%d" % (py(lat), VB_W))
    return "".join(o)


SAT = (
 '<g data-sat class="sat" opacity="0">'
 '<g class="satbody">'
 '<path class="satpan" d="M-13.4 -2.2h7.4v4.4h-7.4zM6 -2.2h7.4v4.4H6z"/>'
 '<path class="satarm" d="M-6 0h-1.2M6 0h1.2"/>'
 '<rect class="satcore" x="-4.6" y="-3.4" width="9.2" height="6.8" rx="1.4"/>'
 '<path class="satant" d="M0 -3.4v-4.2"/>'
 '<circle class="satled" cx="0" cy="-8.4" r="1.3"/>'
 '<path class="satdish" d="M-2.6 3.4h5.2l-1.5 2.6h-2.2z"/>'
 '<circle class="satlens" cx="0" cy="0" r="1.9"/>'
 '</g></g>'
)


def planet_svg():
    land_d, hot_d, counts = dot_paths()
    o = []
    o.append('<div class="wmap" data-planet>')
    o.append('<svg data-world viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet" '
             'role="img" aria-label="World map showing Verysset verification nodes being '
             'scanned by an orbital satellite">' % (VB_W, VB_H))
    o.append('<defs>'
             '<clipPath id="wclip"><rect data-wclip x="0" y="0" width="0" height="%d"/></clipPath>'
             '<linearGradient id="wbeam" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" stop-color="#FFD400" stop-opacity="0"/>'
             '<stop offset=".45" stop-color="#FFD400" stop-opacity=".55"/>'
             '<stop offset="1" stop-color="#FFD400" stop-opacity=".05"/>'
             '</linearGradient>'
             '<radialGradient id="wglow" cx=".5" cy=".5" r=".5">'
             '<stop offset="0" stop-color="#FFD400" stop-opacity=".30"/>'
             '<stop offset="1" stop-color="#FFD400" stop-opacity="0"/>'
             '</radialGradient>'
             '</defs>' % VB_H)
    o.append('<path class="wgrat" d="%s"/>' % graticule())
    o.append('<path class="weq" d="M0 %.0fH%d"/>' % (py(0), VB_W))
    o.append('<g clip-path="url(#wclip)">')
    o.append('<path class="wland" d="%s"/>' % land_d)
    o.append('<path class="whot" d="%s"/>' % hot_d)
    o.append('</g>')
    # orbit trail
    o.append('<path data-orbit class="worbit" d="%s"/>' % ORBIT)
    o.append('<path class="worbitlit" data-orbitlit d="%s"/>' % ORBIT)
    # beam group (positions written by site.js every frame)
    o.append('<g data-beam class="wbeam" opacity="0">'
             '<path data-cone class="wcone" d="M0 0"/>'
             '<path data-core class="wcore" d="M0 0"/>'
             '<circle data-hit class="whit" cx="0" cy="0" r="0"/>'
             '</g>')
    # nodes
    for i, (lon, lat, t, place, detail, inc, sens, side, dy) in enumerate(NODES):
        x, y = px(lon), py(lat)
        o.append('<g class="wn%s" data-k="%d" data-x="%.1f" data-y="%.1f" data-inc="%d">'
                 % (" sens" if sens else "", i, x, y, inc))
        o.append('<circle class="wglow" cx="%.1f" cy="%.1f" r="26" fill="url(#wglow)"/>' % (x, y))
        if sens:
            for r, dl in ((6, 0), (6, 1.1), (6, 2.2)):
                o.append('<circle class="wrip" cx="%.1f" cy="%.1f" r="%d" '
                         'style="transform-origin:%.1fpx %.1fpx;animation-delay:%.1fs"/>'
                         % (x, y, r, x, y, dl))
        o.append('<circle class="wring" cx="%.1f" cy="%.1f" r="9.5"/>' % (x, y))
        o.append('<path class="wret" d="M%.1f %.1fh6.5M%.1f %.1fh6.5M%.1f %.1fv6.5M%.1f %.1fv6.5"/>'
                 % (x - 15.5, y, x + 9, y, x, y - 15.5, x, y + 9))
        o.append('<circle class="wping" cx="%.1f" cy="%.1f" r="9.5" '
                 'style="transform-origin:%.1fpx %.1fpx"/>' % (x, y, x, y))
        o.append('<circle class="wdot" cx="%.1f" cy="%.1f" r="3.1"/>' % (x, y))
        o.append('</g>')
    o.append(SAT)
    o.append('</svg>')
    # HTML label overlay, percentage positioned against the same aspect box
    for i, (lon, lat, t, place, detail, inc, sens, side, dy) in enumerate(NODES):
        x, y = px(lon), py(lat) + dy
        o.append('<div class="wlab %s" data-k="%d" aria-hidden="true" style="left:%.3f%%;top:%.3f%%">'
                 '<span class="wlt">%s</span>'
                 '<span class="wlp">%s</span>'
                 '<span class="wls"><i></i><b>Verifying</b>%s</span>'
                 '</div>' % (side, i, x / VB_W * 100.0, y / VB_H * 100.0, t, place, detail))
    o.append('</div>')
    return "".join(o), counts


def planet_block():
    """Full dark panel: header strip, map, legend, live counters, node ticker."""
    svg, counts = planet_svg()
    o = []
    o.append('<div class="panel planet" data-states="Acquiring|Scanning|Locking|Verified">')
    o.append('<div class="pbarhead"><span class="ptitle">GEO SENTINEL &middot; ORBITAL VERIFICATION SWEEP</span>'
             '<span class="plot">constellation VS-ORB-1 &middot; pass window 90 s &middot; %d cells</span>'
             '<span class="ppills"><span class="pill live"><i></i>Live</span>'
             '<span class="pill on" data-status><i></i>Acquiring</span>'
             '<span class="pill">%d nodes</span></span></div>' % (counts[0] + counts[1], len(NODES)))
    o.append('<div class="pbody">')
    o.append(svg)
    o.append('<div class="wbar">')
    o.append('<div class="wleg">'
             '<span class="wli"><b class="v"></b>Verified node</span>'
             '<span class="wli"><b class="s"></b>Sensor uplink</span>'
             '<span class="wli"><b class="b"></b>Satellite scan beam</span>'
             '<span class="wli"><b class="g"></b>Land coverage grid</span>'
             '</div>')
    o.append('<div class="wstat">'
             '<div class="wsc"><b data-wcount>0</b><i>assets verified</i></div>'
             '<div class="wsc"><b><span data-wlock>0</span>/%d</b><i>nodes locked, this pass</i></div>'
             '<div class="wsc"><b data-wpass>1</b><i>orbital pass</i></div>'
             '</div>' % len(NODES))
    o.append('</div>')
    o.append('</div>')
    o.append('<div class="pfoot"><span>Sensors &middot; field uplink &middot; registry &middot; operations ledger</span>'
             '<span class="right">Continuous sweep &middot; no snapshot, no batch window</span></div>')
    o.append('</div>')
    return "".join(o), counts


def ascii_preview():
    rows = []
    for j in range(ROWS):
        cy = 4 * j + 1
        lat = LAT_TOP - (cy / SX)
        line = []
        for k in range(COLS):
            cx = 4 * k + 1
            lon = (cx / SX) - 180.0
            line.append("#" if is_land(lon, lat) else ".")
        rows.append("".join(line))
    return "\n".join(rows)


if __name__ == "__main__":
    import sys
    if "--ascii" in sys.argv:
        print(ascii_preview())
    else:
        land_d, hot_d, c = dot_paths()
        print("land dots %d (%d B)  hot dots %d (%d B)" % (c[0], len(land_d), c[1], len(hot_d)))
