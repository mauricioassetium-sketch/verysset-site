#!/usr/bin/env python3
"""Static checks for the Verysset multi-page site.
   1. HTML tag balance per file (void elements excluded).
   2. Forbidden characters / strings: em dash, lorem, TODO, gold hexes.
   3. Required: #FFD400 present in the shared CSS, every nav link resolves to a real file.
   4. Local asset references resolve on disk (relative paths, GitHub Pages safe).
"""
import os, re, sys, html, json

ROOT = os.path.dirname(os.path.abspath(__file__))
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr", "path", "circle", "rect", "line", "polyline",
        "polygon", "ellipse", "use", "stop", "animate", "feoffset", "fegaussianblur"}
FAIL = []
WARN = []


def tag_balance(path, src):
    stack, mismatch = [], 0
    # strip comments / script / style bodies
    s = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    s = re.sub(r"<script\b[^>]*>.*?</script>", "<script></script>", s, flags=re.S | re.I)
    s = re.sub(r"<style\b[^>]*>.*?</style>", "<style></style>", s, flags=re.S | re.I)
    for m in re.finditer(r"<(/?)([a-zA-Z][a-zA-Z0-9:-]*)([^>]*?)(/?)>", s):
        closing, name, attrs, selfc = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if name in ("!doctype", "doctype"):
            continue
        if name in VOID or selfc == "/":
            continue
        if not closing:
            stack.append((name, m.start()))
        else:
            if stack and stack[-1][0] == name:
                stack.pop()
            else:
                # tolerate one level of implied close, else count a mismatch
                found = None
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i][0] == name:
                        found = i
                        break
                if found is None:
                    mismatch += 1
                    print("    stray </%s> at offset %d" % (name, m.start()))
                else:
                    for (nm, off) in stack[found + 1:]:
                        mismatch += 1
                        print("    unclosed <%s> at offset %d" % (nm, off))
                    stack = stack[:found]
    for (nm, off) in stack:
        mismatch += 1
        print("    unclosed <%s> at offset %d" % (nm, off))
    return mismatch


# (label, needle, case_insensitive).  TODO / FIXME / PLACEHOLDER are checked
# case SENSITIVELY so the legitimate HTML placeholder="" attribute is not a hit.
BAD_TEXT = [
    ("em dash U+2014", "—", True),
    ("&mdash; entity", "&mdash;", True),
    ("&#8212; entity", "&#8212;", True),
    ("&#x2014; entity", "&#x2014;", True),
    ("en dash U+2013", "–", True),
    ("lorem", "lorem", True),
    ("TODO", "TODO", False),
    ("FIXME", "FIXME", False),
    ("PLACEHOLDER", "PLACEHOLDER", False),
]


def bad_hits(src):
    low = src.lower()
    out = []
    for label, needle, ci in BAD_TEXT:
        n = (low.count(needle.lower()) if ci else src.count(needle))
        if n:
            out.append((label, n))
    return out
GOLD = re.compile(r"#(?:b38a3d|c09a4a|9a7430|faf6ee|c9911f|b8830f|d4af37|cfc4ac|bf9b30|c5a03a)", re.I)

pages = sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))
assets = ["assets/site.css", "assets/site.js"]
print("=" * 72)
print("VERYSSET SITE VERIFICATION")
print("=" * 72)

# --- 1 + 2: per html file
for p in pages:
    src = open(os.path.join(ROOT, p), encoding="utf-8").read()
    print("\n%s  (%.1f KB)" % (p, len(src.encode()) / 1024.0))
    mm = tag_balance(p, src)
    print("  tag balance mismatches : %d %s" % (mm, "OK" if mm == 0 else "FAIL"))
    if mm:
        FAIL.append("%s: %d tag mismatches" % (p, mm))
    hits = bad_hits(src)
    for label, n in hits:
        print("  FORBIDDEN %-16s : %d" % (label, n))
        FAIL.append("%s: %d x %s" % (p, n, label))
    g = GOLD.findall(src)
    if g:
        print("  FORBIDDEN gold hex     : %s" % set(g))
        FAIL.append("%s: gold hex %s" % (p, set(g)))
    print("  no em dash / lorem / TODO / gold : %s" % ("OK" if not hits and not g else "FAIL"))

# --- shared assets
for a in assets:
    src = open(os.path.join(ROOT, a), encoding="utf-8").read()
    print("\n%s  (%.1f KB)" % (a, len(src.encode()) / 1024.0))
    bad = bad_hits(src)
    g = GOLD.findall(src)
    if bad:
        print("  FORBIDDEN: %s" % bad)
        FAIL.append("%s: %s" % (a, bad))
    if g:
        print("  FORBIDDEN gold hex: %s" % set(g))
        FAIL.append("%s: gold hex %s" % (a, set(g)))
    print("  forbidden strings : %s" % ("none OK" if not bad and not g else "FAIL"))

css = open(os.path.join(ROOT, "assets/site.css"), encoding="utf-8").read()
print("\nPalette")
for hexv, label in [("#FFD400", "Verysset yellow"), ("#E6BF00", "yellow hover")]:
    ok = hexv.lower() in css.lower()
    print("  %-8s %-16s : %s" % (hexv, label, "present OK" if ok else "MISSING"))
    if not ok:
        FAIL.append("css missing %s" % hexv)

# --- 3: nav items -> real pages, all internal links resolve
NAV_REQUIRED = ["Home", "How it works", "Engines", "Institutions", "Markets",
                "Tokenization", "Compliance", "FAQ", "Partners", "Contact"]
print("\nNav coverage")
idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
for item in NAV_REQUIRED:
    hit = re.search(r'<a href="([a-z0-9\-]+\.html)"[^>]*>%s</a>' % re.escape(item), idx)
    if hit:
        tgt = hit.group(1)
        ok = os.path.exists(os.path.join(ROOT, tgt))
        print("  %-14s -> %-22s %s" % (item, tgt, "OK" if ok else "MISSING FILE"))
        if not ok:
            FAIL.append("nav %s -> missing %s" % (item, tgt))
    else:
        print("  %-14s -> NOT IN NAV" % item)
        FAIL.append("nav item missing: %s" % item)

# --- footer must carry exactly ONE legal entity, on every page
print("\nFooter entity (must be the single Dubai DIFC entity)")
ONLY_ENT = "Verysset Veritas Ledger Ltd. (Dubai, DIFC)"
REMOVED_ENTS = ["VERYSSET Global Holdings Pte. Ltd.", "VERYSSET Financial Governance FZ LLC"]
for p in pages:
    src = open(os.path.join(ROOT, p), encoding="utf-8").read()
    foot = src[src.find("<footer"):src.find("</footer>")]
    n_ok = foot.count(ONLY_ENT)
    n_bad = sum(foot.count(e) for e in REMOVED_ENTS)
    ents = re.findall(r"(?:Ltd\.|Pte\. Ltd\.|FZ LLC|LLC|Inc\.|GmbH)", foot)
    good = (n_ok == 1 and n_bad == 0 and len(ents) == 1)
    print("  %-22s one entity x%d, removed x%d, entity tokens %d  %s"
          % (p, n_ok, n_bad, len(ents), "OK" if good else "FAIL"))
    if not good:
        FAIL.append("%s: footer entities wrong (ok=%d bad=%d tokens=%d)" % (p, n_ok, n_bad, len(ents)))

print("\nLink and asset resolution")
broken = 0
total = 0
for p in pages:
    src = open(os.path.join(ROOT, p), encoding="utf-8").read()
    refs = re.findall(r'(?:href|src)="([^"#][^"]*)"', src)
    for r in refs:
        if r.startswith(("http://", "https://", "data:", "mailto:", "//")):
            continue
        total += 1
        base = r.split("#")[0].split("?")[0]
        if not base:
            continue
        if not os.path.exists(os.path.join(ROOT, base)):
            print("  BROKEN  %s -> %s" % (p, r))
            broken += 1
    # css url() refs inside inline styles
    for r in re.findall(r'url\((assets/[^)]+)\)', src):
        total += 1
        if not os.path.exists(os.path.join(ROOT, r)):
            print("  BROKEN  %s -> %s" % (p, r))
            broken += 1
print("  relative refs checked : %d" % total)
print("  broken                : %d %s" % (broken, "OK" if broken == 0 else "FAIL"))
if broken:
    FAIL.append("%d broken relative refs" % broken)

# anchors used on pages must exist on the target page
print("\nFragment targets")
frag_bad = 0
for p in pages:
    src = open(os.path.join(ROOT, p), encoding="utf-8").read()
    for r in re.findall(r'href="([a-z0-9\-]*\.html)#([A-Za-z0-9_\-]+)"', src):
        tf, frag = r
        tp = os.path.join(ROOT, tf)
        if not os.path.exists(tp):
            print("  BROKEN page %s -> %s" % (p, tf)); frag_bad += 1; continue
        if ('id="%s"' % frag) not in open(tp, encoding="utf-8").read():
            print("  BROKEN frag %s -> %s#%s" % (p, tf, frag)); frag_bad += 1
    for r in re.findall(r'href="#([A-Za-z0-9_\-]+)"', src):
        if ('id="%s"' % r) not in src:
            print("  BROKEN local frag %s -> #%s" % (p, r)); frag_bad += 1
print("  broken fragments : %d %s" % (frag_bad, "OK" if frag_bad == 0 else "FAIL"))
if frag_bad:
    FAIL.append("%d broken fragments" % frag_bad)

# --- weight budget.
# Split on purpose since round 2: the per-page cost is its own HTML plus its images, while
# site.css + site.js are fetched once and cached across the whole site. site.js now also
# carries the six locale translation catalog, so it gets its own explicit ceiling.
print("\nWeight budget (page html + its images)")
css_sz = os.path.getsize(os.path.join(ROOT, "assets/site.css"))
js_sz = os.path.getsize(os.path.join(ROOT, "assets/site.js"))
for p in pages:
    sz = os.path.getsize(os.path.join(ROOT, p))
    imgs = set()
    src = open(os.path.join(ROOT, p), encoding="utf-8").read()
    for r in re.findall(r'(?:src|url\()="?(assets/[^")]+)', src):
        imgs.add(r)
    for r in re.findall(r'url\((assets/[^)]+)\)', src):
        imgs.add(r)
    isz = sum(os.path.getsize(os.path.join(ROOT, i)) for i in imgs if os.path.exists(os.path.join(ROOT, i)))
    tot = (sz + isz) / 1024.0
    limit = 450 if p == "index.html" else 400
    flag = "OK" if tot <= limit else "OVER"
    print("  %-22s html %5.1f + img %6.1f = %6.1f KB  (limit %d) %s"
          % (p, sz / 1024.0, isz / 1024.0, tot, limit, flag))
    if tot > limit:
        WARN.append("%s over budget: %.1f KB" % (p, tot))
print("  %-22s css %5.1f + js %6.1f = %6.1f KB  (limit %d, cached once) %s"
      % ("shared assets", css_sz / 1024.0, js_sz / 1024.0, (css_sz + js_sz) / 1024.0, 480,
         "OK" if (css_sz + js_sz) / 1024.0 <= 480 else "OVER"))
if (css_sz + js_sz) / 1024.0 > 480:
    WARN.append("shared css+js over budget: %.1f KB" % ((css_sz + js_sz) / 1024.0))

# --- multi language layer
print("\nLanguage layer (6 locales)")
js = open(os.path.join(ROOT, "assets/site.js"), encoding="utf-8").read()
m = re.search(r"var I18N = \{(.*?)\n  \};", js, re.S)
rows = re.findall(r'^\s{4}"([^"]+)":\[(.*)\],?$', m.group(1) if m else "", re.M)
print("  I18N dictionary keys   : %d" % len(rows))
if len(rows) < 400:
    FAIL.append("I18N dictionary too small: %d keys" % len(rows))
short = [k for k, v in rows if len(json.loads("[" + v.rstrip(",") + "]")) != 6]
blank = []
for k, v in rows:
    vals = json.loads("[" + v.rstrip(",") + "]")
    if any((not isinstance(x, str) or not x.strip()) for x in vals):
        blank.append(k)
print("  keys with 6 locales    : %d %s" % (len(rows) - len(short), "OK" if not short else "FAIL"))
print("  keys with a blank value: %d %s" % (len(blank), "OK" if not blank else "FAIL"))
if short:
    FAIL.append("%d i18n keys do not carry 6 locales" % len(short))
if blank:
    FAIL.append("%d i18n keys carry a blank locale" % len(blank))
for p in pages:
    src = open(os.path.join(ROOT, p), encoding="utf-8").read()
    n = len(re.findall(r'data-i18n="', src))
    icon = 'class="lgi"' in src[:src.find("</header>")]
    sel = 'id="langsel"' in src and '<select id="lang"' not in src
    ok = n > 40 and icon and sel
    print("  %-22s %4d marked strings, planet icon %s, icon only selector %s  %s"
          % (p, n, "yes" if icon else "NO", "yes" if sel else "NO", "OK" if ok else "FAIL"))
    if not ok:
        FAIL.append("%s: i18n chrome incomplete (marked=%d icon=%s sel=%s)" % (p, n, icon, sel))

print("\n" + "=" * 72)
if FAIL:
    print("RESULT: FAIL")
    for f in FAIL:
        print("  - " + f)
    sys.exit(1)
print("RESULT: PASS  (0 tag mismatches, no forbidden strings, all links resolve)")
if WARN:
    print("Warnings:")
    for f in WARN:
        print("  - " + f)
