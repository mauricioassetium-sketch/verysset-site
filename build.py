#!/usr/bin/env python3
# Verysset multi-page static site generator.
# Emits one self-contained HTML file per nav item, all sharing assets/site.css + assets/site.js.
# Rule: no em dash anywhere in the output. Hyphens only.

import preloader
import twin
import skyline
import loopkit
import mirror
import pedigree
import jurisdiction
import engines_anim
import rwa
import os, re, io, json, html, hashlib
import mapgen
import i18n_cat
import logogen

OUT = os.path.dirname(os.path.abspath(__file__))

NAV = [
    ("index.html",         "Home"),
    ("how-it-works.html",  "How it works"),
    ("engines.html",       "Engines"),
    ("institutions.html",  "Institutions"),
    ("markets.html",       "Markets"),
    ("tokenization.html",  "Tokenization"),
    ("compliance.html",    "Compliance"),
    ("faq.html",           "FAQ"),
    ("partners.html",      "Partners"),
    ("contact.html",       "Contact"),
]
NAVBAR = NAV[1:9]   # links shown in the desktop bar (Contact is the CTA, Home is the brand)

# The one public contact address. Used on the contact page, in the footer and by the form.
CONTACT_EMAIL = "info@verysset.com"

# Identity (round 10): a flat yellow circle carrying three nested isometric cubes, plus the VERYSSET wordmark.
# The shipped SVG set in assets/ (logo.svg, logo-dark.svg, logo-symbol.svg, logo-symbol-yellow.svg,
# favicon.svg and the legacy verysset-logo*.svg names) is FROZEN: the build no longer regenerates it, it
# only reads the lockup metrics from assets/logo.json to size the header and footer <img> tags.
with open(os.path.join(OUT, "assets", "logo.json"), encoding="utf-8") as _lf:
    LOGO = json.load(_lf)
# Favicon = the circle symbol, bold cut (vector, crisp at 16px). ?v=3 retires the old square from browser caches.
FAVICON = "assets/favicon.svg?v=3"


def logo_img(src, h):
    return ('<img class="blogo" src="%s" alt="Verysset" width="%d" height="%d" decoding="async">'
            % (src, round(h * LOGO["lockup_w"] / LOGO["lockup_h"]), h))

# ---------------------------------------------------------------- i18n machinery
# Strategy: build-side auto-extraction. Every visible text node in the generated HTML
# gets a stable key (slug + md5 of the English source) and is marked with data-i18n.
# The translations live in i18n_cat.py and are injected into assets/site.js as the one
# I18N dictionary the runtime reads. New copy becomes translatable automatically, and an
# untranslated key simply keeps its English text at runtime (never blank, never a key).

I18N_STRINGS = {}          # key -> english text, exactly what textContent will hold
I18N_SEEN = {}             # key -> first page that used it

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_LETTER_RE = re.compile(r"[A-Za-z]")
_WS_RE = re.compile(r"\s+")
I18N_SKIP_TAGS = {"script", "style", "textarea"}
I18N_SVG_TEXT = {"text", "tspan"}
I18N_INLINE = {"span", "b", "i", "em", "strong", "a", "small", "s", "u", "label", "sup", "sub"}

_TOK_RE = re.compile(r"<!--.*?-->|<[^>]*>|[^<]+", re.S)
_TAG_RE = re.compile(r"^<(/?)([a-zA-Z][a-zA-Z0-9:-]*)")
_VOID_T = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
           "param", "source", "track", "wbr", "path", "circle", "rect", "line",
           "polyline", "polygon", "ellipse", "use", "stop", "animate"}


def i18n_norm(raw):
    """Decode entities and collapse whitespace: exactly what textContent returns."""
    return _WS_RE.sub(" ", html.unescape(raw)).strip()


def i18n_key(text):
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    slug = "-".join([x for x in slug.split("-") if x][:7])[:46].strip("-") or "s"
    return "%s.%s" % (slug, hashlib.md5(text.encode("utf-8")).hexdigest()[:4])


def i18n_reg(raw, page=""):
    """Register a string that lives in a data attribute (markets panel, state pills)
       so the runtime can translate it even though it is not a text node yet."""
    txt = i18n_norm(raw)
    if not txt or not _LETTER_RE.search(txt):
        return None
    k = i18n_key(txt)
    I18N_STRINGS[k] = txt
    I18N_SEEN.setdefault(k, page)
    return k


def i18nize(src, page_name=""):
    """Mark every visible text node in one page. A sole text child is marked on its own
       element (flat markup, Clash Display headings keep their font); mixed content gets a
       wrapping span with the surrounding whitespace preserved. SVG <text> is marked on the
       element itself, never wrapped."""
    toks = _TOK_RE.findall(src)
    out = list(toks)
    stack, skip, svg = [], 0, 0
    for i, tk in enumerate(toks):
        if tk.startswith("<!--"):
            continue
        if tk.startswith("<"):
            m = _TAG_RE.match(tk)
            if not m:
                continue
            closing, name = m.group(1), m.group(2).lower()
            if closing:
                if name in I18N_SKIP_TAGS and skip:
                    skip -= 1
                if name == "svg" and svg:
                    svg -= 1
                for j in range(len(stack) - 1, -1, -1):
                    if stack[j][0] == name:
                        del stack[j:]
                        break
                continue
            if name in I18N_SKIP_TAGS:
                skip += 1
            if name == "svg":
                svg += 1
            if "placeholder=\"" in tk and "data-noi18n" not in tk:
                ph = re.search(r'placeholder="([^"]+)"', tk)
                pk = i18n_reg(ph.group(1), page_name) if ph else None
                if pk:
                    out[i] = tk[:-1] + ' data-i18n-ph="%s">' % pk
                    tk = out[i]
            if name in _VOID_T or tk.rstrip().endswith("/>"):
                continue
            stack.append((name, i, ("data-noi18n" in tk or "data-i18n=" in tk)))
            continue
        if skip or not stack or not _LETTER_RE.search(tk):
            continue
        if any(fr[2] for fr in stack):
            continue
        pname, pidx = stack[-1][0], stack[-1][1]
        norm = i18n_norm(tk)
        # the letter test has to run on the DECODED text: "&rarr;" is an arrow, not a word
        if not norm or not _LETTER_RE.search(norm):
            continue
        k = i18n_key(norm)
        core = tk.strip()
        lead, trail = tk[:len(tk) - len(tk.lstrip())], tk[len(tk.rstrip()):]
        sole = (i - 1 == pidx) and (i + 1 < len(toks)) and toks[i + 1].startswith("</")
        padded_inline = (lead or trail) and pname in I18N_INLINE
        if svg:
            if not (pname in I18N_SVG_TEXT and sole):
                continue
            out[pidx] = out[pidx][:-1] + ' data-i18n="%s">' % k
        elif sole and not padded_inline:
            out[pidx] = out[pidx][:-1] + ' data-i18n="%s">' % k
        else:
            out[i] = '%s<span data-i18n="%s">%s</span>%s' % (lead, k, core, trail)
        I18N_STRINGS[k] = norm
        I18N_SEEN.setdefault(k, page_name)
    return "".join(out)


def i18n_report():
    """Write the working catalog and the still-untranslated list, then inject the single
       I18N dictionary into assets/site.js between its generated markers."""
    cat = i18n_cat.CAT
    langs = ["en", "es", "pt", "zh", "ru", "ar"]
    full, missing = 0, []
    dct = {}
    for k in sorted(I18N_STRINGS):
        en = I18N_STRINGS[k]
        row = dict(cat.get(k) or {})
        row["en"] = en
        ok = all(row.get(l) for l in langs)
        if ok:
            full += 1
        else:
            missing.append({"key": k, "en": en, "page": I18N_SEEN.get(k, "")})
            for l in langs:
                if not row.get(l):
                    row[l] = en          # graceful fallback: English, never blank
        dct[k] = [row[l] for l in langs]
    for k, row in sorted(i18n_cat.EXTRA.items()):
        dct[k] = [row.get(l) or row["en"] for l in langs]
    js = ["/* ==== I18N:BEGIN generated by build.py from i18n_cat.py. Do not hand edit. ==== */",
          "  var I18N_LANGS = ['en','es','pt','zh','ru','ar'];",
          "  var I18N = {"]
    keys = sorted(dct)
    for n, k in enumerate(keys):
        vals = ",".join(json.dumps(v, ensure_ascii=False) for v in dct[k])
        js.append("    %s:[%s]%s" % (json.dumps(k), vals, "" if n == len(keys) - 1 else ","))
    js.append("  };")
    js.append("  /* ==== I18N:END ==== */")
    block = "\n".join(js)
    path = os.path.join(OUT, "assets", "site.js")
    src = open(path, encoding="utf-8").read()
    pat = re.compile(r"/\* ==== I18N:BEGIN.*?==== \*/.*?/\* ==== I18N:END ==== \*/", re.S)
    if pat.search(src):
        src = pat.sub(lambda _m: block, src)
    else:
        raise SystemExit("site.js is missing the I18N:BEGIN / I18N:END markers")
    open(path, "w", encoding="utf-8").write(src)
    with open(os.path.join(OUT, "i18n_missing.json"), "w", encoding="utf-8") as f:
        json.dump(missing, f, ensure_ascii=False, indent=1)
    return len(I18N_STRINGS), full, len(missing)


# ---------------------------------------------------------------- icons (24x24 grid)
ICONS = {
    "ingest":  "M12 3v11m0 0-4-4m4 4 4-4M4 17v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3",
    "geo":     "M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17ZM3.5 12h17M12 3.5c2.6 2.5 2.6 14.5 0 17-2.6-2.5-2.6-14.5 0-17M12 10.6a1.4 1.4 0 1 0 0 2.8 1.4 1.4 0 0 0 0-2.8",
    "aura":    "M12 9.2a2.8 2.8 0 1 0 0 5.6 2.8 2.8 0 0 0 0-5.6M12 4.5A7.5 7.5 0 0 1 19.5 12M12 19.5A7.5 7.5 0 0 1 4.5 12M12 1.2A10.8 10.8 0 0 1 22.8 12M12 22.8A10.8 10.8 0 0 1 1.2 12",
    "ledger":  "M5 20V9m4.7 11V4m4.6 16v-8m4.7 8V7M3 21.5h18",
    "score":   "M4 17a8 8 0 1 1 16 0M12 17l4.5-5.2M12 17a1 1 0 1 0 0-2 1 1 0 0 0 0 2",
    "anchor":  "m12 2.6 8.2 4.7v9.4L12 21.4 3.8 16.7V7.3ZM8.4 12l2.6 2.6L15.9 9.6",
    "bank":    "M2.6 9 12 3.6 21.4 9M4.8 9v8.4m4.6-8.4v8.4m5.2-8.4v8.4m4.6-8.4v8.4M2.6 20.4h18.8",
    "token":   "m12 2.6 8.2 4.7v9.4L12 21.4 3.8 16.7V7.3Zm0 5.1 3.9 2.2v4.4L12 16.5l-3.9-2.2V9.9Z",
    "shield":  "M12 2.6 4.4 5.9v6c0 4.4 3.1 8.5 7.6 9.6 4.5-1.1 7.6-5.2 7.6-9.6v-6Zm-3.4 9.3 2.5 2.5 4.6-4.9",
    "doc":     "M6.4 2.6h7.4l4.2 4.3v14.5H6.4ZM13.6 2.6v4.6h4.4M9.2 12h6M9.2 15.6h6M9.2 8.4h2.6",
    "chain":   "M10 13.8a3.6 3.6 0 0 0 5.4.4l2.6-2.6a3.6 3.6 0 0 0-5.1-5.1l-1.5 1.5M14 10.2a3.6 3.6 0 0 0-5.4-.4L6 12.4a3.6 3.6 0 0 0 5.1 5.1l1.5-1.5",
    "pulse":   "M2.6 12h4l2.4-6.6L13.4 19l2.6-7h5.4",
    "vault":   "M3.4 4.6h17.2v14.8H3.4Zm8.6 3.1a4.3 4.3 0 1 0 0 8.6 4.3 4.3 0 0 0 0-8.6M12 4.6v3.1m0 8.6v3.1m4.3-7.4h4.3m-17.2 0h4.3",
    "globe":   "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M3.3 9.8h17.4M3.3 14.2h17.4M12 3c2.6 2.6 2.6 15.4 0 18-2.6-2.6-2.6-15.4 0-18",
}

# ---------------------------------------------------------------- markets icons (24x24 line grid)
# One fixed, hand-authored mark per institutional mandate. Twelve distinct silhouettes,
# stroke-only so they inherit currentColor and light up yellow when the mandate is active.
MARKET_ICONS = [
    # 01 Carbon Credits - leaf
    "M20.5 3.5c0 9.4-4.6 15.2-10.4 15.2-3.3 0-5.8-2.3-5.8-5.6 0-6.6 8.4-9.6 16.2-9.6Z"
    "M4.5 20.5c3-6 7.5-11 13.5-14",
    # 02 Institutional Financial Markets - axis with a rising trend
    "M3.5 3.5v17h17M7 15.6l3.9-4.7 3.2 2.7 5.4-6.6M19.5 7h-3.7M19.5 7v3.7",
    # 03 RWA & Tokenization - hex token
    "m12 2.6 8.2 4.7v9.4L12 21.4 3.8 16.7V7.3Zm0 5.1 3.9 2.2v4.4L12 16.5l-3.9-2.2V9.9Z",
    # 04 Mining & Natural Resources - faceted gem
    "M6.2 3.4h11.6l3.6 6.1L12 20.8 2.6 9.5ZM2.6 9.5h18.8M9.2 3.4 6.6 9.5 12 20.8"
    "M14.8 3.4l2.6 6.1L12 20.8",
    # 05 Energy & Infrastructure - bolt
    "M13.6 2.4 4.4 13.9h6.4l-0.8 7.7 9.6-11.8h-6.6Z",
    # 06 Institutional Real Estate - tower with windows
    "M3.4 20.6h17.2M5.6 20.6V5.4l7-2.8v18M12.6 9.6l6 2.1v8.9"
    "M8 8.4h1.6M8 12h1.6M8 15.6h1.6M15.4 13.6h1.2M15.4 16.6h1.2",
    # 07 Environmental & Carbon Markets - globe
    "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M3.3 9.8h17.4M3.3 14.2h17.4"
    "M12 3c2.6 2.6 2.6 15.4 0 18-2.6-2.6-2.6-15.4 0-18",
    # 08 Commodities & Extractive - stacked crates
    "M3.2 13.6h7.2v7H3.2ZM13.6 13.6h7.2v7h-7.2ZM8.4 6.4h7.2v7H8.4Z"
    "M6.8 13.6v7M17.2 13.6v7M12 6.4v7",
    # 09 Public & Sovereign Sector - columned landmark under a standard
    "M12 1.4v2.4M12 1.4h3.2l-1.1 1.2 1.1 1.2H12M2.6 10.2 12 4.4l9.4 5.8"
    "M5.1 10.2v8.3M9.7 10.2v8.3M14.3 10.2v8.3M18.9 10.2v8.3M2.6 21h18.8",
    # 10 Insurance & Reinsurance - shield with check
    "M12 2.4 4.4 5.6v6.2c0 4.5 3.2 8.6 7.6 9.8 4.4-1.2 7.6-5.3 7.6-9.8V5.6Z"
    "M8.6 11.8l2.6 2.6 4.4-4.8",
    # 11 Agriculture & Food Supply Chain - sprout
    "M12 20.6v-7.1M12 13.5C12 9.9 9.1 7 5.5 7c0 3.6 2.9 6.5 6.5 6.5Z"
    "M12 13.5C12 10.5 14.4 8 17.4 8c0 3-2.4 5.5-5.4 5.5ZM7 20.6h10",
    # 12 Transport, Logistics & Mobility - truck
    "M2.6 6.4h10.8v9.1H2.6ZM13.4 9.9h3.7l3.3 3.2v2.4h-7Z"
    "M7.2 18.4a2 2 0 1 0 0-4 2 2 0 0 0 0 4M17.6 18.4a2 2 0 1 0 0-4 2 2 0 0 0 0 4"
    "M2.6 15.5h2.6M9.2 15.5h4.4",
]


def market_icon(i, cls="mic"):
    """Inline 24x24 line mark for mandate i (0-based). No icon font, no external library."""
    return ('<svg class="%s" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" '
            'focusable="false"><path d="%s"/></svg>' % (cls, MARKET_ICONS[i]))


def icon_path(name, cx, cy, size=24, cls="pn-ic"):
    s = size / 24.0
    tx = cx - size / 2.0
    ty = cy - size / 2.0
    return ('<g transform="translate(%.2f,%.2f) scale(%.4f)"><path class="%s" d="%s"/></g>'
            % (tx, ty, s, cls, ICONS[name]))


# ---------------------------------------------------------------- process-line SVG builder
def procsvg(nodes, width=1160, box_w=None, box_h=78, top_label_y=44, sub_y=None, svg_h=206):
    """nodes: list of dicts {t, s, icon}. Builds the AO-HUA style left-to-right unit line:
       a base rail, per-gap segments, unit blocks, and a pulse that rides the rail."""
    n = len(nodes)
    pad = 34
    span = width - pad * 2
    step = span / float(n)
    if box_w is None:
        box_w = min(128, step * 0.74)
    cy = 112
    sub_y = sub_y if sub_y is not None else cy + box_h / 2 + 26
    xs = [pad + step * (i + 0.5) for i in range(n)]

    o = []
    o.append('<svg data-proc viewBox="0 0 %d %d" role="img" aria-label="Verysset process line" '
             'preserveAspectRatio="xMidYMid meet">' % (width, svg_h))
    # axis guides
    o.append('<path class="axis" d="M%.1f 22H%.1f"/>' % (pad, width - pad))
    o.append('<path class="axis" d="M%.1f %d H%.1f"/>' % (pad, svg_h - 16, width - pad))
    # base rail
    o.append('<path class="flowbase" d="M%.1f %d H%.1f"/>' % (xs[0], cy, xs[-1]))
    # per-gap lit segments
    for i in range(n - 1):
        a = xs[i] + box_w / 2
        b = xs[i + 1] - box_w / 2
        o.append('<path class="seg" data-k="%d" d="M%.1f %d H%.1f"/>' % (i, a, cy, b))
        # arrow head
        mx = (a + b) / 2.0
        o.append('<path class="seg" data-k="%d" d="m%.1f %d 7 4-7 4" fill="none"/>' % (i, mx - 3, cy - 4))
    # unit blocks
    for i, nd in enumerate(nodes):
        x = xs[i]
        o.append('<g class="pn" data-k="%d">' % i)
        o.append('<rect class="pn-box" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="4"/>'
                 % (x - box_w / 2, cy - box_h / 2, box_w, box_h))
        o.append(icon_path(nd["icon"], x, cy, 26))
        o.append('<text class="pn-t" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x, top_label_y, nd["t"]))
        o.append('<text class="pn-s" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (x, sub_y, nd["s"]))
        o.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%02d</text>' % (x, 16, i + 1))
        o.append('</g>')
    # the animated rail that draws itself, plus the pulse
    o.append('<path data-flow class="flowpath" d="M%.1f %d H%.1f"/>' % (xs[0], cy, xs[-1]))
    o.append('<g data-pulse opacity="0"><circle class="pulse-h" r="11"/><circle class="pulse" r="4.2"/></g>')
    o.append('</svg>')
    return "".join(o)


def mbal(cells):
    """mass-balance style summary strip. cells: list of (label, value, dec, unit)."""
    o = ['<div class="mbal">']
    for lab, val, dec, unit in cells:
        o.append('<div class="mcell"><div class="ml">%s</div><div class="mv">'
                 '<span data-to="%s" data-dec="%d">0</span><span class="mu">%s</span></div></div>'
                 % (lab, val, dec, unit))
    o.append('</div>')
    return "".join(o)


def panel(title, lot, pills, body, foot_left, foot_right, states=None, drive=None, extra_cls=""):
    for _s in (states or "").split("|"):
        i18n_reg(_s)                       # state names live in an attribute, not a text node
    st = ' data-states="%s"' % states if states else ""
    dr = ' data-drive="%s"' % drive if drive else ""
    pl = "".join(pills)
    return ('<div class="panel procline %s"%s%s>'
            '<div class="pbarhead"><span class="ptitle">%s</span><span class="plot">%s</span>'
            '<span class="ppills">%s</span></div>'
            '<div class="pbody">%s</div>'
            '<div class="pfoot"><span>%s</span><span class="right">%s</span></div>'
            '</div>') % (extra_cls, st, dr, title, lot, pl, body, foot_left, foot_right)


PILL_LIVE = '<span class="pill live"><i></i>Live</span>'
def pill_status(txt):
    return '<span class="pill on" data-status><i></i>%s</span>' % txt
def pill(txt):
    return '<span class="pill">%s</span>' % txt


# ---------------------------------------------------------------- shell
def head(title, desc, page, noindex=False):
    return """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
%s<meta name="theme-color" content="#ffffff">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="%s">
<link rel="preload" href="assets/fonts/ClashDisplay-Medium.otf" as="font" type="font/otf" crossorigin>
<link rel="preload" href="assets/fonts/ClashDisplay-Semibold.otf" as="font" type="font/otf" crossorigin>
<link rel="preload" href="assets/fonts/Inter-Variable.ttf" as="font" type="font/ttf" crossorigin>
<link rel="stylesheet" href="assets/site.css">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<div class="pbar" aria-hidden="true"></div>
%s
<main id="main">""" % (title, desc, '<meta name="robots" content="noindex,nofollow">\n' if noindex else "",
       title, desc, FAVICON, navbar(page))


LANGS = [("en", "English"), ("es", "Espa\u00f1ol"), ("pt", "Portugu\u00eas"),
         ("zh", "\u4e2d\u6587"), ("ru", "\u0420\u0443\u0441\u0441\u043a\u0438\u0439"),
         ("ar", "\u0627\u0644\u0639\u0631\u0628\u064a\u0629")]


def lang_select():
    """Language control: an icon only globe button that opens a light listbox of the six
       languages, each written in its own script. The names are fixed native names and are
       never translated (data-noi18n), so every reader can find their own language.
       Open state, keyboard support and aria state are wired in assets/site.js (langMenu)."""
    check = ('<svg class="lck" viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" '
             'focusable="false"><path d="M3.4 8.6 6.5 11.6 12.6 4.6"/></svg>')
    opts = "".join('<li role="option" id="lopt-%s" data-lang="%s" lang="%s" aria-selected="%s">%s'
                   '<span class="lnm"%s>%s</span></li>'
                   % (c, c, c, "true" if c == "en" else "false", check,
                      ' dir="rtl"' if c == "ar" else "", n)
                   for c, n in LANGS)
    return ('<div class="lang" data-noi18n>'
            '<button type="button" id="langsel" class="lbtn" title="Language" aria-label="Language" '
            'aria-haspopup="listbox" aria-expanded="false" aria-controls="langlist">'
            '<svg class="lgi" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" '
            'focusable="false"><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M3.3 9.8h17.4'
            'M3.3 14.2h17.4M12 3c2.6 2.6 2.6 15.4 0 18-2.6-2.6-2.6-15.4 0-18"/></svg>'
            '<svg class="lchev" viewBox="0 0 8 5" width="7" height="5" aria-hidden="true" '
            'focusable="false"><path d="M1 1.1 4 3.9 7 1.1"/></svg>'
            '</button>'
            '<ul class="lmenu" id="langlist" role="listbox" aria-label="Language" tabindex="-1">%s</ul>'
            '</div>') % opts


def navbar(page):
    links = "".join('<a href="%s"%s>%s</a>'
                    % (h, ' class="cur" aria-current="page"' if h == page else "", t)
                    for h, t in NAVBAR)
    dlinks = "".join('<a href="%s"%s>%s</a>'
                     % (h, ' class="cur" aria-current="page"' if h == page else "", t)
                     for h, t in NAV)
    return """<header class="nav" id="nav"><div class="nrow">
<a class="brand" href="index.html" aria-label="Verysset home">%s</a>
<nav class="nmenu" aria-label="Primary">%s</nav>
<div class="nact">%s<a class="btn sm" href="contact.html">Request a meeting</a>
<button class="burg" id="burg" aria-label="Menu" aria-expanded="false" aria-controls="drawer"><span></span></button></div>
</div><div class="drawer" id="drawer">%s<a class="btn" href="contact.html">Request a meeting</a></div></header>""" % (logo_img("assets/logo.svg", 32), links, lang_select(), dlinks)


def pgnav(prev, nxt):
    o = ['<div class="wrap"><div class="pgnav">']
    if prev:
        o.append('<a href="%s"><span class="pl">Previous</span><span class="pt">%s</span></a>' % prev)
    else:
        o.append('<a href="index.html"><span class="pl">Back to</span><span class="pt">Home</span></a>')
    if nxt:
        o.append('<a class="next" href="%s"><span class="pl">Next</span><span class="pt">%s</span></a>' % nxt)
    else:
        o.append('<a class="next" href="contact.html"><span class="pl">Next</span><span class="pt">Request a meeting</span></a>')
    o.append('</div></div>')
    return "".join(o)

# ---------------------------------------------------------------- hero strip + footer badge icons

# Live verified assets counter (hero strip, section 1). ONE source of truth for the model:
#   value(date) = VA_BASE_M + VA_STEP_M * floor(days since VA_ANCHOR / VA_DAYS)   (US$ millions)
# The numbers ship to the browser as data-va-* attributes and site.js recomputes on every load
# from the visitor's clock (UTC, no network). The build only bakes the first paint / SEO text.
VA_ANCHOR = "2026-09-12"     # UTC midnight; the counter reads exactly VA_BASE_M on this day
VA_BASE_M = 4276             # US$ 4,276 million = US$ 4.276 billion
VA_STEP_M = 13               # + US$ 13 million ...
VA_DAYS = 10                 # ... every 10 days


def va_value_m(day=None):
    import datetime
    a = datetime.date.fromisoformat(VA_ANCHOR)
    t = day or datetime.datetime.now(datetime.timezone.utc).date()
    return VA_BASE_M + VA_STEP_M * max(0, (t - a).days // VA_DAYS)


def va_billions(m):
    """4276 -> '4.276', 4300 -> '4.3', 5000 -> '5' (integer math, no float drift)."""
    ip, fp = divmod(int(m), 1000)
    fp = ("%03d" % fp).rstrip("0")
    return "%d.%s" % (ip, fp) if fp else "%d" % ip

# 24x24, stroke based (1.5px, currentColor), the .acf detail carries the #FFD400 accent.
def _svg(cls, title, body):
    return ('<svg class="%s" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            '<title>%s</title>%s</svg>' % (cls, title, body))

STAT_ICONS = {
    "vassets": _svg("ci", "Verified assets ledger",
                    '<path class="acf" d="M2.6 10.2 12 2.8l9.4 7.4z"/>'
                    '<path d="M5.6 13v4.8M9.9 13v4.8M14.1 13v4.8M18.4 13v4.8M3 20.8h18"/>'),
    "sat": _svg("ci", "Continuous satellite verification",
                '<path class="acf" d="M13 8l3 3-3 3-3-3z"/>'
                '<path d="M11.1 4.9 9.1 2.9 4.9 7.1 6.9 9.1z"/><path d="M21.1 14.9 19.1 12.9 14.9 17.1 16.9 19.1z"/>'
                '<path d="M11.5 9.5 9 7M14.5 12.5 17 15"/>'
                '<path d="M3 14.5a6.5 6.5 0 0 1 6.5 6.5M3 17.8a3.2 3.2 0 0 1 3.2 3.2"/>'
                '<circle class="acf" cx="3.6" cy="20.4" r="1.1"/>'),
    "interop": _svg("ci", "Institutional interoperability network",
                    '<circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/>'
                    '<circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>'
                    '<path d="M6.5 6.5 10 10M17.5 6.5 14 10M6.5 17.5 10 14M17.5 17.5 14 14M7 5h10M7 19h10"/>'
                    '<circle class="acf" cx="12" cy="12" r="2.8"/>'),
}

STAT_ICONS.update({
    "modes": _svg("ci", "Verification modes converging",
                  '<rect x="3" y="3" width="6" height="6" rx="1.2"/><rect x="15" y="3" width="6" height="6" rx="1.2"/>'
                  '<rect x="3" y="15" width="6" height="6" rx="1.2"/><rect x="15" y="15" width="6" height="6" rx="1.2"/>'
                  '<path d="M9 9l1.3 1.3M15 9l-1.3 1.3M9 15l1.3-1.3M15 15l-1.3-1.3"/>'
                  '<circle class="acf" cx="12" cy="12" r="2.2"/>'),
    "replica": _svg("ci", "Digital twin replica accuracy",
                    '<rect x="3" y="3" width="12" height="12" rx="1.5"/>'
                    '<rect x="9" y="9" width="12" height="12" rx="1.5" stroke-dasharray="2.2 2.2"/>'
                    '<rect class="acf" x="9" y="9" width="6" height="6"/>'),
    "layers": _svg("ci", "Digital twin layers",
                   '<path class="acf" d="M12 3.2 20.5 7.6 12 12 3.5 7.6z"/>'
                   '<path d="M3.5 12 12 16.4 20.5 12M3.5 16.4 12 20.8 20.5 16.4"/>'),
    "chain": _svg("ci", "Data pedigree chain",
                  '<path d="M10 7.5H7.2a4.5 4.5 0 0 0 0 9H10M14 7.5h2.8a4.5 4.5 0 0 1 0 9H14"/>'
                  '<rect class="acf" x="7.5" y="10.8" width="9" height="2.4" rx="1.2"/>'),
})

BADGE_ICONS = {
    "interop": _svg("fbi", "Interoperability",
                    '<path d="M4 8.5h14M15 5l3.5 3.5L15 12M20 15.5H6M9 12l-3.5 3.5L9 19"/>'
                    '<circle class="acf" cx="12" cy="12" r="1.6"/>'),
    "lock": _svg("fbi", "Information security",
                 '<path d="M12 3l7 2.8v5.4c0 4.3-2.9 7.9-7 9.6-4.1-1.7-7-5.3-7-9.6V5.8z"/>'
                 '<rect class="acf" x="9" y="11" width="6" height="4.6" rx="1"/>'
                 '<path d="M10.2 11V9.6a1.8 1.8 0 0 1 3.6 0V11"/>'),
    "cont": _svg("fbi", "Business continuity",
                 '<path d="M19.5 12a7.5 7.5 0 0 1-12.8 5.3M4.5 12a7.5 7.5 0 0 1 12.8-5.3"/>'
                 '<path d="M17.3 3.1v3.6h-3.6M6.7 20.9v-3.6h3.6"/>'
                 '<circle class="acf" cx="12" cy="12" r="2"/>'),
}

DISCLAIMER = (
    'Disclaimer: Verysset does not tokenize assets, does not act as a broker, dealer, exchange, custodian, or financial '
    'advisor, and does not execute trading operations on its own behalf or on behalf of third parties. Verysset is not '
    'authorized or regulated by the Dubai Financial Services Authority (DFSA) and does not provide any financial services '
    'within or from the Dubai International Financial Centre (DIFC). Verysset is solely a provider of technology '
    'infrastructure and software, an activity that does not constitute a &quot;financial service&quot; under the DIFC '
    'Regulatory Law 2004 and does not require a DFSA license. Nothing contained on this website constitutes an offer, '
    'solicitation, recommendation, or investment advice. Any reference to digital assets, tokens, or financial '
    'instruments is for informational purposes only and does not imply that Verysset engages in such activities. Use of '
    'our services does not create a fiduciary, intermediary, or wealth management relationship. Each user is responsible '
    'for complying with the applicable regulations in their jurisdiction.')


FOOT = """</main>
<footer><div class="wrap">
<a class="brand" href="index.html" aria-label="Verysset home">LOGO_DARK_TOKEN</a>
<div class="fgrid"><div>
<p>Verysset is a sovereign infrastructure for the continuous verification of real world assets.</p>
<p class="ents">Verysset Veritas Ledger Ltd. (Dubai, DIFC)</p>
<p class="ents">Innovation Hub, Level 14, Gate Village Building 4<br>Dubai International Financial Centre (DIFC)<br>Dubai, United Arab Emirates</p></div>
<div class="fcol"><h5>Platform</h5><a href="how-it-works.html">How it works</a><a href="engines.html">Engines</a><a href="how-it-works.html#services">Services</a><a href="markets.html">Markets</a></div>
<div class="fcol"><h5>Institutions</h5><a href="institutions.html">Actors &amp; audit</a><a href="compliance.html#licensing">Licensing</a><a href="compliance.html#governance">Governance</a><a href="faq.html">FAQ</a></div>
<div class="fcol"><h5>Contact</h5><a href="mailto:CONTACT_EMAIL_TOKEN">CONTACT_EMAIL_TOKEN</a><a href="contact.html">Request a meeting</a><a href="compliance.html#jurisdiction">Jurisdiction</a><a href="compliance.html">Legal</a><a href="partners.html">Partners</a></div>
</div>
<div class="fbot"><span class="fcopy">&copy; 2026 VERYSSET. All rights reserved.</span>
<div class="fstd"><span class="fstdl">Standards-aligned infrastructure</span><ul class="fbadges" aria-label="Standards-aligned infrastructure: ISO 20022, ISO 27001, ISO 27002, ISO 22301"><li class="fbadge">BADGE_INTEROP<span>ISO 20022</span><small>aligned</small></li><li class="fbadge">BADGE_LOCK<span>ISO 27001 / 27002</span><small>aligned</small></li><li class="fbadge">BADGE_CONT<span>ISO 22301</span><small>aligned</small></li></ul></div></div>
<div class="fdisc" lang="en" dir="ltr" data-noi18n><p>DISCLAIMER_TOKEN</p></div>
</div></footer>
<button class="ttop" aria-label="Back to top"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5m-7 7 7-7 7 7"/></svg></button>
<script src="assets/site.js"></script>
</body></html>"""


def page(fname, title, desc, body, prev=None, nxt=None, pgn=True, noindex=False):
    doc = head(title, desc, fname, noindex) + body
    if fname == "index.html":          # satellite verification preloader, home only
        doc = doc.replace("</head><body>", "</head><body>" + preloader.preloader(), 1)
    if pgn:
        doc += '<section class="sec tight">' + pgnav(prev, nxt) + '</section>'
    doc += (FOOT.replace('CONTACT_EMAIL_TOKEN', CONTACT_EMAIL).replace('DISCLAIMER_TOKEN', DISCLAIMER)
            .replace('BADGE_INTEROP', BADGE_ICONS['interop']).replace('BADGE_LOCK', BADGE_ICONS['lock'])
            .replace('BADGE_CONT', BADGE_ICONS['cont'])
            .replace('LOGO_DARK_TOKEN', logo_img("assets/logo-dark.svg", 44)))
    doc = i18nize(doc, fname)
    with open(os.path.join(OUT, fname), "w", encoding="utf-8") as f:
        f.write(doc)
    return len(doc)


def phead(crumb, eb, h1, lede, extra=""):
    return ('<section class="phead"><div class="wrap">'
            '<div class="crumb rv"><b>Verysset</b><i></i><span>%s</span></div>'
            '<span class="eb rv" data-i="1">%s</span>'
            '<h1 class="rv" data-i="2" style="margin-top:18px">%s</h1>'
            '<p class="lede rv" data-i="3">%s</p>%s</div></section>') % (crumb, eb, h1, lede, extra)


def cta(head_txt, sub, btn="Request institutional meeting"):
    return ('<section class="sec"><div class="wrap"><div class="ctab rv">'
            '<div><h2>%s</h2><p>%s</p></div>'
            '<div class="acts"><a class="btn yl" href="contact.html">%s</a>'
            '<a class="btn gh" href="how-it-works.html">See how it works</a></div>'
            '</div></div></section>') % (head_txt, sub, btn)


# ---------------------------------------------------------------- shared content blocks
ENGINES = [
    ("01", "geo", "Geo Sentinel",
     "Physical, geospatial and temporal verification system that records events, location and operational conditions throughout the asset&rsquo;s lifecycle.",
     "geo.webp", "Geo Sentinel field capture",
     ["Location and perimeter events", "Operating conditions over time", "Timestamped chain of custody", "Sensor and field evidence intake"]),
    ("02", "aura", "Aura Verification Engine",
     "AI based continuous verification engine that persistently evaluates integrity, coherence and consistency of asset information.",
     "aura.webp", "Aura verification engine",
     ["Integrity checks on every record", "Cross source coherence tests", "Anomaly and drift detection", "Continuous re-evaluation, not batch"]),
    ("03", "ledger", "Pedigree Engine",
     "Custody system for the asset&rsquo;s verifiable history that generates a dynamic trust score from the quality, consistency and continuity of evidence.",
     "pedigree.webp", "Pedigree engine ledger",
     ["Full evidence lineage retained", "Dynamic trust score output", "Reconstructable end to end history", "Score linked to instruments"]),
]

# Institutions & actors: facts from the Assetium presentation (v4 EN). Auditor names are set
# as plain typographic badges, never the firms' logos (trademarks).
AUDITORS = ["Deloitte", "PwC", "EY", "KPMG"]

PEDIGREE = [("01", "Source capture"), ("02", "Source authentication"), ("03", "Ingestion &amp; cleaning"),
            ("04", "Cross-validation"), ("05", "Twin integration"), ("06", "DLT registration")]

# Low to high, so the band reads 0 to 100 in reading direction and mirrors under dir=rtl.
# Segments are equal width on purpose: the printed ranges carry the scale, the bar carries order.
TRUST_BANDS = [("hold", "Hold", "&lt;60"), ("watch", "Watch", "60-74"), ("std", "Standard", "75-84"),
               ("prem", "Premium", "85-89"), ("ent", "Enterprise", "90-100")]

# Verification modes, grouped by where the evidence comes from. Each mode carries a flat 24px icon
# (ink strokes, one yellow accent) and a one line description. Names are unchanged, so their keys hold.
def _mi(body):
    return '<svg class="ci" viewBox="0 0 24 24" aria-hidden="true" focusable="false">%s</svg>' % body

MODE_ICONS = {
    "optical": _mi('<path d="M2.5 4.5H7v3H2.5zM17 4.5h4.5v3H17zM7 6h2.5M14.5 6H17"/>'
                   '<rect class="acf" x="9.5" y="3.5" width="5" height="5" rx=".8"/>'
                   '<path d="M10.5 11.5 6.5 19.5M13.5 11.5l4 8" stroke-dasharray="1.6 2.2"/><path d="M4 20.5h16"/>'),
    "sar": _mi('<circle class="acf" cx="5" cy="5" r="1.9"/><path d="M9.5 5A4.5 4.5 0 0 1 5 9.5M13.5 5A8.5 8.5 0 0 1 5 13.5"/>'
               '<path d="M11.2 21h7.3a3 3 0 0 0 .5-5.96 4.3 4.3 0 0 0-8.2-.84A3.4 3.4 0 0 0 11.2 21z"/>'),
    "lidar": _mi('<path d="M12 8.5 19 12v6.5L12 22l-7-3.5V12zM5 12l7 3.5 7-3.5M12 15.5V22"/>'
                 '<path d="M10.8 4.4 5.6 11M13.2 4.4l5.2 6.6" stroke-dasharray="1.6 2"/>'
                 '<circle class="acf" cx="12" cy="3" r="1.8"/>'),
    "drone": _mi('<path d="M9.5 9.5 7.7 7.7M14.5 9.5l1.8-1.8M9.5 14.5l-1.8 1.8M14.5 14.5l1.8 1.8"/>'
                 '<circle cx="5.5" cy="5.5" r="3"/><circle cx="18.5" cy="5.5" r="3"/>'
                 '<circle cx="5.5" cy="18.5" r="3"/><circle cx="18.5" cy="18.5" r="3"/>'
                 '<rect class="acf" x="9" y="9" width="6" height="6" rx="1.2"/>'),
    "thermal": _mi('<rect x="2.5" y="7.5" width="14" height="11" rx="1.6"/><path d="M6 7.5 7.3 5h4.4L13 7.5"/>'
                   '<circle class="acf" cx="9.5" cy="13" r="3"/>'
                   '<path d="M20.5 6.5c1.3 1.25 1.3 2.75 0 4s-1.3 2.75 0 4 1.3 2.75 0 4"/>'),
    "iot": _mi('<path d="M3.5 13.5H6M3.5 17.5H6M18 13.5h2.5M18 17.5h2.5M9.4 6.2a3.8 3.8 0 0 1 5.2 0M7 3.6a7.2 7.2 0 0 1 10 0"/>'
               '<rect x="6" y="9.5" width="12" height="12" rx="1.6"/>'
               '<rect class="acf" x="9.5" y="13" width="5" height="5" rx=".6"/>'),
    "env": _mi('<path class="acf" d="M6 18C6 10 11 5 19.5 4.5 19 13 14 18 6 18z"/><path d="M4 20 13 11"/>'
               '<path d="M5 3s-2 2.4-2 3.7a2 2 0 0 0 4 0C7 5.4 5 3 5 3z"/>'),
    "meter": _mi('<rect x="3.5" y="3.5" width="17" height="17" rx="2"/>'
                 '<path class="acf" d="M13 6.5 8.5 13H12l-1 4.5 4.5-6.5H12z"/>'),
    "h2": _mi('<path d="M9.5 3.5h5M10.5 3.5v5.3L5 18.6c-.5.9.1 2.2 1.2 2.2h11.6c1.1 0 1.7-1.3 1.2-2.2L13.5 8.8V3.5M7.8 13.5h8.4"/>'
              '<circle class="acf" cx="10.3" cy="17.2" r="1.7"/><circle class="acf" cx="14" cy="16.2" r="1.1"/>'),
    "bim": _mi('<path d="M5 21V7.5l7-4 7 4V21M3 21h18M9 10.5h2M13 10.5h2M9 14h2M13 14h2"/>'
               '<rect class="acf" x="10.3" y="17" width="3.4" height="4"/>'),
    "field": _mi('<path d="M12 21.5s-6.5-6.1-6.5-11a6.5 6.5 0 0 1 13 0c0 4.9-6.5 11-6.5 11z"/>'
                 '<circle class="acf" cx="12" cy="10.5" r="2.6"/>'),
    "registry": _mi('<path d="M5.5 2.5h9l4 4v15h-13z"/><path class="acf" d="M14.5 2.5v4h4z"/>'
                    '<path d="M8.5 11h7v7h-7zM12 11v7M8.5 14.5h7"/>'),
    "regulator": _mi('<path d="M3 8.5 12 3.5l9 5zM5.5 11.5v6M9.8 11.5v6M14.2 11.5v6M18.5 11.5v6"/>'
                     '<rect class="acf" x="3" y="19.5" width="18" height="2.5" rx=".4"/>'),
    "exchange": _mi('<path d="M2.5 21l1.8-4.5h6.4L12.5 21zM11.5 21l1.8-4.5h6.4l1.8 4.5z"/>'
                    '<path class="acf" d="M7 15.5l1.8-4.5h6.4L17 15.5z"/>'),
    "carbon": _mi('<path d="M7 3.5V7M7 15v5.5M12 6v4M12 15v4M17 2.5V6M17 12v4.5"/>'
                  '<rect x="5.5" y="7" width="3" height="8" rx=".5"/><rect class="acf" x="10.5" y="10" width="3" height="5" rx=".5"/>'
                  '<rect x="15.5" y="6" width="3" height="6" rx=".5"/>'),
    "refdata": _mi('<path d="M5 6v12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>'
                   '<ellipse class="acf" cx="12" cy="6" rx="7" ry="2.5"/>'),
    "standards": _mi('<path d="M8.6 14.6 7 21.5l5-2.6 5 2.6-1.6-6.9"/><circle cx="12" cy="9.5" r="6.5"/>'
                     '<circle class="acf" cx="12" cy="9.5" r="3"/>'),
}

VERIFY_GROUPS = [
    ("Remote sensing", [
        ("optical", "Optical satellite imagery", "Wide-area imagery that tracks change over time."),
        ("sar", "SAR radar, all-weather 24/7", "Sees through cloud, smoke and darkness."),
        ("lidar", "LiDAR 3D precision mapping", "Precise 3D models of terrain and structures."),
        ("drone", "Drone fleets (fixed-wing, multirotor, BVLOS)", "Close-range aerial surveys, flown on demand."),
        ("thermal", "Infrared &amp; thermal cameras", "Heat signatures that reveal activity and faults."),
    ]),
    ("On-site sensing", [
        ("iot", "Industrial IoT sensors", "Live operating data, straight from the equipment."),
        ("env", "Environmental sensors", "Air, water and soil conditions at the asset."),
        ("meter", "Smart energy meters", "Generation and consumption, metered in real time."),
        ("h2", "H2 quality analyzers", "Hydrogen purity, measured at the point of output."),
        ("bim", "BIM &amp; building sensors", "Building models linked to live condition data."),
        ("field", "Regional field verification services", "Local inspectors confirm evidence on the ground."),
    ]),
    ("Registries, markets &amp; standards", [
        ("registry", "Public registries &amp; land records", "Title and ownership, checked at the source."),
        ("regulator", "Regulatory bodies", "Permits, licenses and official filings."),
        ("exchange", "Commodity &amp; metals exchanges", "Benchmark prices and settlement records."),
        ("carbon", "Carbon &amp; energy markets", "Credit issuance, retirement and energy prices."),
        ("refdata", "Reference financial data providers", "Pricing and reference data for valuation."),
        ("standards", "International standards &amp; certification", "Recognized frameworks every check is held to."),
    ]),
]
VERIFY_MODES = [name for _g, items in VERIFY_GROUPS for _ic, name, _d in items]


def verify_modes_block():
    """Trust Score card footer: three groups, each mode = icon tile + name + one line description."""
    o = ['<div class="ia-src"><span class="ia-srl">Verification modes include</span><div class="ia-mg">']
    for gi, (grp, items) in enumerate(VERIFY_GROUPS):
        o.append('<div class="ia-mgp"><h4 class="ia-mgh"><span class="ia-mgn" aria-hidden="true">%02d</span>'
                 '<span>%s</span></h4><ul class="ia-ml">' % (gi + 1, grp))
        o.extend('<li><span class="ia-mi">%s</span><div class="ia-mt"><b>%s</b><span class="ia-md">%s</span></div></li>'
                 % (MODE_ICONS[ic], name, desc) for ic, name, desc in items)
        o.append('</ul></div>')
    o.append('</div></div>')
    return "".join(o)

IA_STATS = [("modes", "100+", "Verification modes",
             "Optical, SAR radar, LiDAR, drones, IoT and registries, cross-validated per asset."),
            ("replica", "99.9%", "Replica accuracy",
             "Fidelity of every digital twin to the physical asset it mirrors."),
            ("layers", "9", "Twin layers",
             "Nine layers compose every digital twin, audited in its first year after launch."),
            ("chain", "6", "Data pedigree stages",
             "From source capture to DLT registration, stage by stage.")]

MARKETS = [
    ("01", "Carbon Credits", "End to end verification of carbon assets, from origination to retirement."),
    ("02", "Institutional Financial Markets", "Continuous assurance across securities, derivatives and structured products."),
    ("03", "RWA &amp; Tokenization", "Real time provenance for every tokenized real world asset."),
    ("04", "Mining &amp; Natural Resources", "Verifiable proof of reserves, production and custody."),
    ("05", "Energy &amp; Infrastructure", "Live integrity for generation, transmission and infrastructure assets."),
    ("06", "Institutional Real Estate", "Ongoing verification of title, condition and valuation."),
    ("07", "Environmental &amp; Carbon Markets", "Auditable environmental claims and market compliance."),
    ("08", "Commodities &amp; Extractive", "Traceable custody from extraction to settlement."),
    ("09", "Public &amp; Sovereign Sector", "Sovereign grade evidence for public assets and programs."),
    ("10", "Insurance &amp; Reinsurance", "Continuous underwriting evidence and claims integrity."),
    ("11", "Agriculture &amp; Food Supply Chain", "Verified provenance across the agrifood value chain."),
    ("12", "Transport, Logistics &amp; Mobility", "Continuous verification of fleet, cargo and infrastructure."),
]

# Three stat blocks per mandate, rendered in the markets panel. Kept as ranges and
# qualitative spans: the claim is the cadence of the evidence, never a fabricated figure.
MARKET_STATS = [
    [("Continuous", "Verification cadence"), ("15 to 30%", "Audit cost reduction"),
     ("Full lifecycle", "Origination to retirement")],
    [("Real time", "Assurance cadence"), ("T+0", "Evidence availability"),
     ("Multi asset", "Securities, derivatives, structured")],
    [("Per token", "Provenance record"), ("1 to 1", "Asset to evidence link"),
     ("On demand", "Regulator access")],
    [("Per shipment", "Custody checkpoint"), ("Reserves to sale", "Chain coverage"),
     ("20 to 35%", "Reconciliation effort cut")],
    [("24 / 7", "Integrity monitoring"), ("Per asset", "Condition record"),
     ("Generation to grid", "Coverage span")],
    [("Ongoing", "Title and condition checks"), ("Per property", "Evidence file"),
     ("10 to 25%", "Due diligence time saved")],
    [("Claim level", "Auditability"), ("Continuous", "Compliance record"),
     ("Multi registry", "Reporting interoperability")],
    [("Extraction to settlement", "Custody trail"), ("Per lot", "Traceability unit"),
     ("Append only", "Evidence ledger")],
    [("Sovereign grade", "Evidence standard"), ("Program level", "Reporting scope"),
     ("Continuous", "Public asset oversight")],
    [("Current condition", "Risk pricing basis"), ("Claim level", "Integrity checks"),
     ("Continuous", "Underwriting evidence")],
    [("Farm to shelf", "Provenance span"), ("Per batch", "Traceability unit"),
     ("Continuous", "Supply chain evidence")],
    [("Fleet wide", "Asset coverage"), ("In transit", "Cargo verification"),
     ("Continuous", "Infrastructure integrity")],
]


# RWA & Tokenization leads every mandate list (operator, 2026-09-13). MARKETS, MARKET_STATS and
# MARKET_ICONS are index aligned, so they move together; numbering is reissued 01..12 afterwards.
MARKET_LEAD = 2


def _lead_first(seq, i):
    return [seq[i]] + seq[:i] + seq[i + 1:]


MARKETS = [("%02d" % (k + 1), t, dsc) for k, (_, t, dsc) in enumerate(_lead_first(MARKETS, MARKET_LEAD))]
MARKET_STATS = _lead_first(MARKET_STATS, MARKET_LEAD)
MARKET_ICONS = _lead_first(MARKET_ICONS, MARKET_LEAD)


def market_stats_attr(i):
    """Pack a mandate's stat blocks into one data attribute the panel script unpacks."""
    for v, l in MARKET_STATS[i]:
        i18n_reg(v, "markets.html"); i18n_reg(l, "markets.html")
    return "|".join("%s~%s" % (v, l) for v, l in MARKET_STATS[i])


def market_stats_html(i):
    return "".join('<div class="mst"><b>%s</b><i>%s</i></div>' % (v, l) for v, l in MARKET_STATS[i])


VALIDATION = [
    ("Evaluation in real environments", "Operational validation with complex assets under institutional control standards."),
    ("Functional separation", "Clear separation between verification, custody, financial operation and banking supervision."),
    ("ISO 20022 compatibility", "Alignment with global institutional banking interoperability standards."),
    ("Event based verification", "Continuous asset monitoring with auditable events and asset states."),
    ("Flexible integration", "REST and service oriented APIs for institutional systems."),
    ("Institutional evaluation", "Formal evaluation processes for controlled environments."),
]

SERVICES = [
    ("01", "Continuous verification", "Persistent verification from physical, legal and operational evidence, replacing point in time audits."),
    ("02", "Verifiable digital twin", "A living digital twin reflecting the real state of the asset throughout its lifecycle."),
    ("03", "Data Pedigree custody", "Complete history of evidence, events and changes as a persistent source of truth."),
    ("04", "Dynamic trust score", "Objective trust metrics based on quality, consistency and continuity of verified evidence."),
    ("05", "Verification as a Service", "Recurring verification adapted to the criticality and frequency required by each asset."),
    ("06", "RWA anchoring &amp; tokenization", "Linking tokenized assets to their verifiable digital twin for measurable trust."),
]
# RWA anchoring & tokenization leads the service stack too (same operator request), renumbered 01..06.
SERVICES = [("%02d" % (k + 1), h, p2) for k, (_, h, p2) in enumerate(_lead_first(SERVICES, 5))]

FAQS = [
    ("What is the asset trust score?",
     "A dynamic, objective metric that reflects the quality, consistency and continuity of the verified evidence behind a real world asset, updated continuously rather than at a single point in time."),
    ("What parameters does Verysset use to calculate the trust score?",
     "Physical, geospatial, temporal, legal and operational evidence, evaluated for integrity, coherence and continuity by the Aura Verification Engine and the Pedigree Engine."),
    ("Does the trust score imply a financial valuation of the asset?",
     "No. The trust score measures the verifiability and integrity of evidence, not price or financial value. Verysset does not price, trade, or value assets."),
    ("Does Verysset replace auditors or regulators?",
     "No. Verysset provides continuous, auditable evidence that strengthens the work of auditors and regulators. It does not replace their roles or responsibilities."),
    ("Is Verysset an audit company?",
     "No. Verysset is a verification and evidence custody infrastructure layer, not an audit firm."),
    ("Is Verysset a blockchain company?",
     "Verysset is blockchain agnostic. Its verification ledger integrates with Polymesh, Asentrix and ERC 3643 where applicable, but verification itself is independent of any single chain."),
    ("Does Verysset custody assets or funds?",
     "No. Verysset does not custody funds or securities and does not assume fiduciary responsibilities."),
    ("Is Verysset compatible with MiCA, MAS, or VARA?",
     "Yes. Verysset is designed to coexist with frameworks such as MiCA (EU), MAS (Singapore), VARA (Dubai) and FATF standards, without replacing the obligations of user entities."),
    ("Does Verysset use Zero Knowledge Proofs (ZKP)?",
     "Verysset&rsquo;s architecture supports verifiable privacy mechanisms, including Zero Knowledge Proofs, to prove attributes of evidence without exposing the underlying confidential data."),
    ("In which jurisdiction does Verysset operate?",
     "Verysset is incorporated in Dubai (UAE), with entities in Singapore and Dubai, and operates under a jurisdiction agnostic model aligned with MAS, VARA, MiCA and FATF standards."),
]

# href, name, file, render height px, intrinsic width, intrinsic height
PARTNERS = [
    ("https://www.dvaex.io/",              "DVA",             "dva.webp",           30, 127,   40),
    ("https://cbi-difc.com/",              "Capital Bridge",  "capitalbridge.webp", 36, 111,   40),
    ("https://www.apexgroup.com/",         "Apex Group",      "apex.svg",           38, 549.6, 514.1),
    ("https://truleumventures.com/",       "Truleum",         "truleum.webp",       24, 240,   40),
    ("https://tokeny.com/",                "Tokeny",          "tokeny.webp",        32, 40,    40),
    ("https://www.ndcglobal.ae/",          "NDC",             "ndc.svg",            22, 972,   344),
    ("https://www.mercadobitcoin.com.br/", "Mercado Bitcoin", "mercadobitcoin.svg", 34, 74,    74),
    ("https://www.hextrust.com/",          "Hex Trust",       "hextrust.svg",       18, 372.6, 59.7),
    ("https://upay.com/",                  "Upay",            "upay.webp",          26, 240,   64),
    # evidence layer partners: earth observation, industrial IoT, sensors, audit.
    # Official marks as vector (assets/real-<slug>.svg, cropped to a tight viewBox).
    ("https://www.planet.com/",                   "Planet",          "planet.svg",         30, 244.9, 122.1),
    ("https://www.siemens.com/en-us/",            "Siemens",         "siemens.svg",        22, 199.6, 35.1),
    ("https://www.bosch-sensortec.com/en",        "Bosch Sensortec", "boschsensortec.svg", 26, 441.7, 105.1),
    ("https://www.tdk.com/en/index.html",         "TDK",             "tdk.svg",            26, 699.8, 157.7),
    ("https://www.pwc.in/",                       "PwC India",       "pwcindia.svg",       34, 71.3,  35.2),
    # technology and advisory partners (round 11). Vector marks, tight viewBox.
    ("https://aradina.net",                       "ARADINA Technology", "aradina.svg",     34, 529.4, 155.1),
    ("https://www.enlightenedminds.io/",          "Enlightened Minds",  "enlightenedminds.svg", 30, 262.8, 62.3),
    ("https://orijins.ai/",                       "Orijins",            "orijins.svg",     34, 146.8, 46),
]

NOCARDS = [
    ("No custody",        "Does not custody funds, securities, or manage third party resources."),
    ("No issuance",       "Does not issue financial instruments nor represent assets in markets."),
    ("No trading",        "Does not participate in pricing, trading, or settlement."),
    ("No fiduciary risk", "Does not assume fiduciary risk or financial responsibilities."),
]


def engines_cards(link=True):
    o = ['<div class="g3 mt">']
    for i, (n, ic, name, desc, img, alt, bullets) in enumerate(ENGINES):
        o.append('<article class="tcard rv" data-i="%d"><div class="thead">'
                 '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="%s"/></svg>'
                 '<span class="tn">%s</span></div><h3>%s</h3><p>%s</p></article>' % (i, ICONS[ic], n, name, desc))
    o.append('</div>')
    return "".join(o)


def vgrid():
    o = ['<div class="vgrid mt">']
    for i, (h, p) in enumerate(VALIDATION):
        o.append('<div class="v rv" data-i="%d"><div class="vm"></div><h4>%s</h4><p>%s</p></div>' % (i, h, p))
    o.append('</div>')
    return "".join(o)


def faq_block():
    o = ['<div class="faq mt">']
    for i, (q, a) in enumerate(FAQS):
        o.append('<div class="fi rv" data-i="%d">'
                 '<button class="fq" id="fq%d" aria-expanded="false" aria-controls="fa%d">'
                 '<span>%s</span><span class="pm" aria-hidden="true"></span></button>'
                 '<div class="fa" id="fa%d" role="region" aria-labelledby="fq%d"><p>%s</p></div></div>'
                 % (min(i, 6), i, i, q, i, i, a))
    o.append('</div>')
    return "".join(o)


def partner_logo_file(f):
    """Prefer a recovered real brand asset (assets/real-<slug>.<ext>) when one is present,
       otherwise keep the local file. Resolved at build time against the filesystem so a
       failed recovery silently falls back instead of emitting a broken <img>."""
    slug = os.path.splitext(f)[0]
    for ext in ("svg", "png", "webp", "jpg", "jpeg"):
        cand = "real-%s.%s" % (slug, ext)
        if os.path.exists(os.path.join(OUT, "assets", cand)):
            return cand, True
    return f, False


def partner_grid():
    """One grid, one version. A single <img> per cell inside a fixed contain-box, so any
       aspect ratio renders legibly on white. Rest state is desaturated; hover restores the
       brand colour. Plain CSS filters, no mask compositing (masks were rendering blank)."""
    o = ['<div class="pgrid">']
    n = len(PARTNERS)
    rd, rt = n % 5, n % 3  # partners left on a short last row at 5 columns (desktop) / 3 (tablet)
    for i, (href, name, f, h, iw, ih) in enumerate(PARTNERS):
        src, real = partner_logo_file(f)
        # Stretch a short last row to full width (site.css .pl-d* / .pl-t* on the 60 track grid)
        # so no track is left empty and the gray grid background never shows as a blank cell.
        cls = ("" if not rd or i < n - rd else " pl-d%d" % rd) + ("" if not rt or i < n - rt else " pl-t%d" % rt)
        o.append('<a class="pcell%s rv" data-i="%d" href="%s" target="_blank" rel="noopener noreferrer" '
                 'title="%s" aria-label="%s">' % (cls, min(i, 6), href, name, name))
        o.append('<span class="pw">')
        o.append('<img class="plogo" src="assets/%s" alt="%s" width="172" height="52" '
                 'loading="lazy" decoding="async">' % (src, name))
        o.append('</span>')
        o.append('<span class="pname">%s</span></a>' % name)
    # Closing cell: 17 partners + 1 invitation. Desktop 5 columns = 3 full rows + a last row of 2
    # stretched cells (pl-d2), tablet 3 columns = 5 full rows + 2 stretched (pl-t2); the invitation
    # then takes its own full width row. Mobile 2 columns = 8 rows + 1 partner, and the invitation
    # sits inline beside it (an even count adds pj-row so it spans instead). No gray orphan slot.
    o.append('<a class="pcell pjoin%s rv" data-i="6" href="contact.html">' % ("" if n % 2 else " pj-row") +
             '<span class="pjt"><span class="pje">Your institution</span>'
             '<span class="pjh">Become a partner</span><i class="pja" aria-hidden="true">&rarr;</i></span></a>')
    o.append('</div>')
    return "".join(o)


# ---------------------------------------------------------------- governance map block
def governance_map():
    """The map image plus an animated SVG overlay: connectors drawn on scroll,
       nodes revealed in sequence, legend faded in."""
    # coordinates in the image's own 1289 x 357 space
    nodes = [
        (0, 812, 150, "PHYSICAL ASSET",  "start"),
        (1, 800, 300, "EVIDENCE INTAKE", "start"),
        (2, 978, 168, "VERYSSET CORE",   "middle"),
        (3, 1120, 92, "VERIFIED TWIN",   "middle"),
        (4, 1196, 246, "INSTITUTIONS",   "middle"),
    ]
    wires = [
        "M812 150 L900 196 L978 168",
        "M800 300 L920 246 L978 168",
        "M978 168 L1052 130 L1120 92",
        "M978 168 L1086 208 L1196 246",
    ]
    o = ['<div class="govstage rv">']
    o.append('<div class="gmapbox">')
    o.append('<img class="gmap" src="assets/map.webp" width="1289" height="357" '
             'alt="Verysset governance topology: physical asset, verification core and institutional systems" loading="lazy" decoding="async">')
    o.append('<svg class="govsvg" viewBox="0 0 1289 357" preserveAspectRatio="xMidYMid meet" aria-hidden="true">')
    for i, wpth in enumerate(wires):
        cls = "gwire" + (" dim" if i > 2 else "")
        o.append('<path class="%s" d="%s"/>' % (cls, wpth))
    for k, x, y, label, anchor in nodes:
        dx = 14 if anchor == "start" else 0
        ty = y - 20 if anchor == "middle" else y + 26
        ta = "middle" if anchor == "middle" else "start"
        o.append('<g class="gnode" data-k="%d">' % k)
        o.append('<circle class="gr" cx="%d" cy="%d" r="15"/>' % (x, y))
        o.append('<circle class="gd" cx="%d" cy="%d" r="4.2"/>' % (x, y))
        o.append('<text x="%d" y="%d" text-anchor="%s">%s</text>' % (x + (dx if ta == "start" else 0), ty, ta, label))
        o.append('</g>')
    o.append('</svg>')
    o.append('</div>')
    o.append('<div class="govcopy">')
    o.append('<span class="eb">Governance topology</span>')
    o.append('<h3>One verification layer between the asset and the institution.</h3>')
    o.append('<p>Evidence enters from the field. The verification core evaluates it continuously, '
             'custodies its lineage and publishes a verified twin. Institutional systems consume the '
             'result, never the raw operation.</p>')
    o.append('<div class="glegend">')
    for lab, hollow in [("Physical asset and field evidence", False),
                        ("Verysset verification core", False),
                        ("Verified digital twin", True),
                        ("Institutional and regulatory systems", True)]:
        o.append('<span class="gli"><b%s></b>%s</span>' % (' class="o"' if hollow else '', lab))
    o.append('</div></div></div>')
    return "".join(o)


# ---------------------------------------------------------------- pages
def build_index():
    show_nodes = [
        {"t": "INGEST",   "s": "field &middot; legal &middot; ops", "icon": "ingest"},
        {"t": "GEO",      "s": "place &middot; time",               "icon": "geo"},
        {"t": "AURA",     "s": "integrity &middot; coherence",      "icon": "aura"},
        {"t": "PEDIGREE", "s": "lineage custody",                   "icon": "ledger"},
        {"t": "SCORE",    "s": "dynamic trust",                     "icon": "score"},
        {"t": "ANCHOR",   "s": "instrument link",                   "icon": "anchor"},
        {"t": "INSTITUTION", "s": "bank &middot; regulator",        "icon": "bank"},
    ]
    show_panel = panel(
        "VERYSSET &middot; CONTINUOUS VERIFICATION LINE",
        "asset VS-2691 &middot; campaign feed live &middot; 7 stages gated",
        [PILL_LIVE, pill_status("Idle"), pill("ISO 20022")],
        procsvg(show_nodes) + mbal([
            ("Evidence ingested", "100", 0, "%"),
            ("Integrity checks", "99.2", 1, "%"),
            ("Continuity", "98.6", 1, "%"),
            ("Trust score", "87.4", 1, ""),
            ("Anchored lots", "24", 0, ""),
        ]),
        "Sources &middot; field sensors &middot; legal registry &middot; operations ledger",
        "Stage 1 of 7 &middot; the verification line",
        states="Idle|Ingesting|Geo locked|Verifying|Scoring|Anchoring|Anchored",
        drive="pin")

    tok_nodes = [
        {"t": "INGEST", "s": "evidence verified",   "icon": "ingest"},
        {"t": "SCORE",  "s": "pedigree engine",     "icon": "score"},
        {"t": "ANCHOR", "s": "smart contract link", "icon": "token"},
    ]
    tok_panel = panel(
        "TOKENIZATION LINE &middot; INGEST / SCORE / ANCHOR",
        "lot VS-2691 &middot; campaign 04 &middot; 3 stages",
        [PILL_LIVE, pill_status("Ingesting"), pill("ERC 3643")],
        procsvg(tok_nodes, width=880) + mbal([
            ("Evidence accepted", "100", 0, "%"),
            ("Score published", "87.4", 1, ""),
            ("Anchor confirmed", "100", 0, "%"),
        ]),
        "Anchoring &middot; Polymesh &middot; Asentrix &middot; ERC 3643",
        "Trust is measured, not declared",
        states="Ingesting|Scoring|Anchored")

    b = []
    # hero
    b.append('<section class="hero"><div class="wrap">')
    b.append('<span class="eb nb rv">Verysset&reg; &middot; Sovereign grade verification for real world assets</span>')
    # looping "real world assets." underline (rwa.py): live text, animated SVG bar, replaces the em::after wipe
    b.append('<h1 class="rv" data-i="1">Sovereign grade verification for ' + rwa.em() + '</h1>')
    b.append('<p class="hsub rv" data-i="2">Continuous, auditable trust. The evidence banks and regulators accept. '
             'One verifiable truth layer for institutional capital.</p>')
    b.append('<div class="hcta rv" data-i="3"><a class="btn" href="contact.html">Request institutional meeting</a>'
             '<a class="tl" href="how-it-works.html">See how it works <span class="ar">&rarr;</span></a></div>')
    va_b = va_billions(va_value_m())
    b.append('<ul class="chips rv" data-i="4" aria-label="Verysset live network metrics: verified assets, continuous verification, ISO 20022 interoperability">'
             '<li class="chip" data-va-anchor="%s" data-va-base="%d" data-va-step="%d" data-va-days="%d">'
             % (VA_ANCHOR, VA_BASE_M, VA_STEP_M, VA_DAYS) +
             '<span class="cib">' + STAT_ICONS["vassets"] + '</span><div class="cbd">'
             '<b><span class="va-n" data-noi18n>$' + va_b + 'B</span></b>'
             '<span class="cl"><span class="dot"></span><span class="va-l" data-noi18n>Live &middot; over '
             '<bdi class="va-a">$' + va_b + ' billion</bdi> in verified assets</span></span>'
             '<p class="cc">Real world asset value verified across the network, growing as new evidence clears.</p></div></li>'
             '<li class="chip"><span class="cib">' + STAT_ICONS["sat"] + '</span><div class="cbd">'
             '<b>24/7</b><span class="cl">Continuous verification</span>'
             '<p class="cc">Satellite sweeps and event monitoring never pause.</p></div></li>'
             '<li class="chip"><span class="cib">' + STAT_ICONS["interop"] + '</span><div class="cbd">'
             '<b>ISO&nbsp;20022<span class="u">aligned</span></b><span class="cl">Institutional interoperability</span>'
             '<p class="cc">Native message format for global banking rails.</p></div></li>'
             '</ul>')
    b.append('</div></section>')

    # pinned showcase
    b.append('<div class="showwrap" id="showwrap"><div class="showstage">')
    b.append('<div class="grid" aria-hidden="true"></div>')
    b.append('<div class="showstat">Scroll to run the line</div>')
    b.append('<div class="showin">')
    b.append('<div class="showhead"><span class="eb nb">How the Verysset system works</span>'
             '<h2>Evidence enters. Verification never stops.</h2>'
             '<p>Seven stages, one continuous line. Scroll to move a live lot through ingestion, '
             'geospatial capture, AI verification, lineage custody, scoring and anchoring, all the way '
             'to the institution that consumes the result.</p></div>')
    b.append(show_panel)
    b.append('</div>')
    b.append('<div class="showcue"><i></i>Keep scrolling<i></i></div>')
    b.append('</div></div>')

    # planet map - the orbital verification sweep (centrepiece)
    pmap, pcounts = mapgen.planet_block()
    for _s in ("Acquiring", "Scanning", "Locking", "Verified"):
        i18n_reg(_s, "index.html")
    b.append('<section class="sec planetsec" id="planet"><div class="wrap">')
    b.append('<div class="head-split"><div class="rv"><span class="eb">Geo Sentinel &middot; planetary coverage</span>'
             '<h2 class="t">One verification layer. Every jurisdiction that matters.</h2></div>'
             '<div class="rv" data-i="1"><p class="lede" style="margin-top:0">Geo Sentinel is the orbital sweep of the '
             'Verysset network. Field sensors publish upward, the constellation locks each asset cell in sequence, and '
             'the verified state lands in the ledger before an auditor could open a file.</p>'
             '<p class="lede">Twelve live cells below, across eleven jurisdictions and every populated continent. '
             'Real estate in the DIFC, carbon in the Amazon, lithium in the Atacama, ports in Singapore: the same '
             'evidence standard, verified continuously, never declared.</p></div></div>')
    b.append('<div class="mt rv">' + pmap + '</div>')
    b.append('<div class="wtick rv" data-i="1" aria-hidden="true"><div class="wtickrow">')
    for _rep in range(2):
        for _n in mapgen.NODES:
            b.append('<span class="wtk"><i></i>%s<b>%s</b></span>' % (_n[2], _n[3]))
    b.append('</div></div>')
    b.append('<div class="wnote rv" data-i="2"><span class="eb nb">Coverage grid</span>'
             '<p>%d land cells sampled, %d inside an active verification radius. The sweep is continuous: '
             'every pass re-locks every node, because a verification that stops being checked stops being true.</p></div>'
             % (pcounts[0] + pcounts[1], pcounts[1]))
    b.append('</div></section>')

    # problem
    b.append('<section class="sec alt" id="problem"><div class="wrap">')
    b.append('<div class="head-split"><div class="rv"><span class="eb">The structural problem</span>'
             '<h2 class="t">Trillions in RWA and security tokens rely on verification that is static, punctual and fragmented.</h2></div>'
             '<div class="rv" data-i="1"><p class="lede" style="margin-top:0">Real world assets and security tokens move in real time. '
             'Their verification still runs on point in time audits: delayed, declarative and detached from the asset itself.</p>'
             '<p class="lede">The problem is not a lack of capital. The problem is that a mobile market runs on static trust: '
             'reports that are filed, not measured; claims that are asserted, not proven.</p></div></div>')
    b.append('<div class="g3 mt">'
             '<div class="card rv" data-i="0"><div class="rule"></div><h3>Static</h3><p>Verification frozen in silos and reports.</p></div>'
             '<div class="card rv" data-i="1"><div class="rule"></div><h3>Delayed</h3><p>Audits arrive after the fact, never live.</p></div>'
             '<div class="card rv" data-i="2"><div class="rule"></div><h3>Unmeasurable</h3><p>Trust is asserted, never really measured.</p></div></div>')
    b.append('</div></section>')

    # solution
    b.append('<section class="sec" id="solution"><div class="wrap">')
    b.append('<div class="g2b"><div class="rv"><span class="eb">The solution</span>'
             '<h2 class="t w">A sovereign layer of trust, built to operate under institutional standards.</h2>'
             '<div class="mt2"><a class="tl" href="engines.html">Explore the architecture <span class="ar">&rarr;</span></a></div></div>'
             '<div class="rv" data-i="1"><p class="lede" style="margin-top:6px">Verysset is a neutral verification infrastructure that '
             'connects the reality of the asset with financial, regulatory, and market systems, designed for continuous, '
             'measurable, traceable verification.</p>'
             '<p class="lede">A world of moving assets needs moving verification. That is where Verysset enters: a sovereign, '
             'continuous verification infrastructure that turns static snapshots into live, measurable trust across the entire '
             'life of an RWA or security token.</p></div></div>')
    b.append('<div class="mt" style="border:1px solid var(--line);border-radius:3px;overflow:hidden;background:var(--bg)">'
             '<img class="clipr" src="assets/solution.webp" alt="Verysset verification architecture overview" '
             'style="display:block;width:100%;height:auto" loading="lazy" decoding="async"></div>')
    b.append('</div></section>')

    # governance map
    b.append('<section class="sec alt" id="governance"><div class="wrap">')
    b.append('<div class="head-split"><div class="rv"><span class="eb">Governance map</span>'
             '<h2 class="t">The system, alive and in one view.</h2></div>'
             '<div class="rv" data-i="1"><p class="lede" style="margin-top:0">Verification, custody, financial operation and '
             'supervision stay structurally distinct. The map below shows how evidence travels between them, and where '
             'Verysset sits: in the middle, neutral, and never in the trade.</p></div></div>')
    b.append('<div class="mt">' + governance_map() + '</div>')
    b.append('</div></section>')

    # engines teaser
    b.append('<section class="sec" id="engines"><div class="wrap">')
    b.append('<div class="ctr rv" style="max-width:820px;margin:0 auto"><span class="eb nb">Core technologies</span>'
             '<h2 class="t">Three engines. One verifiable truth.</h2>'
             '<p class="lede">Technology in service of institutional control, not speculation.</p></div>')
    b.append(engines_cards())
    b.append('<div class="ctr mt2"><a class="tl" href="engines.html">Open the engine detail <span class="ar">&rarr;</span></a></div>')
    b.append('</div></section>')

    # tokenization strip
    b.append('<section class="sec ink-band"><div class="wrap">')
    b.append('<div class="head-split"><div class="rv"><span class="eb">RWA &amp; tokenization model</span>'
             '<h2 class="t">Tokenization anchored to observable truth.</h2></div>'
             '<div class="rv" data-i="1"><p class="lede" style="margin-top:0">Verysset acts as the sovereign verification layer '
             'anchoring tokenized assets to a verifiable digital twin, continuously fed by validated evidence. '
             'Tokenization is based on measurable, observable, real time trust, not static declarations.</p>'
             '<div class="mt2"><a class="tl" href="tokenization.html">See the tokenization line <span class="ar">&rarr;</span></a></div></div></div>')
    b.append('<div class="mt rv">' + tok_panel + '</div>')
    b.append('</div></section>')

    # explore grid
    b.append('<section class="sec alt"><div class="wrap">')
    b.append('<div class="rv"><span class="eb">Explore</span><h2 class="t">Everything, one page at a time.</h2></div>')
    b.append('<div class="g3 mt">')
    for i, (href, kn, t, p) in enumerate([
        ("tokenization.html", "RWA", "Tokenization", "Ingest, score and anchor: the process line that links instruments to evidence."),
        ("how-it-works.html", "Platform", "How it works", "Structured ingestion, continuous verification, custody and scoring, plus the full service stack."),
        ("engines.html", "Technology", "The three engines", "Geo Sentinel, the Aura Verification Engine and the Pedigree Engine in detail."),
        ("institutions.html", "Institutions", "Validation and audit", "Validation criteria, Big 4 audited digital twins and the continuous Trust Score."),
        ("markets.html", "Mandates", "Twelve markets", "One verification infrastructure applied across every class of institutional capital."),
        ("compliance.html", "Legal", "Compliance and DIFC", "Neutral by design, DIFC incorporated, aligned with MiCA, MAS, VARA and FATF."),
    ]):
        b.append('<a class="kcard%s rv" data-i="%d" href="%s"><span class="kn">%s</span><h3>%s</h3><p>%s</p>'
                 '<span class="go">Open <span>&rarr;</span></span></a>' % (" lead" if i == 0 else "", i % 3, href, kn, t, p))
    b.append('</div>')
    b.append('</div></section>')

    b.append(cta("Operate real world assets under continuous verification.",
                 "If your institution needs to operate real world assets under continuous verification and clear trust metrics, "
                 "Verysset provides the sovereign infrastructure to do so with control and confidence."))

    return page("index.html",
                "Verysset | Sovereign Grade Verification for Real World Assets",
                "Sovereign grade continuous verification for real world assets. Auditable trust for institutional capital that banks and regulators accept.",
                "".join(b), pgn=False)


def build_how():
    nodes = [
        {"t": "INGEST",   "s": "structured intake",   "icon": "ingest"},
        {"t": "VERIFY",   "s": "continuous checks",   "icon": "aura"},
        {"t": "CUSTODY",  "s": "lineage &middot; score", "icon": "vault"},
    ]
    p = panel("VERIFICATION LINE &middot; STEP 01 / 02 / 03",
              "asset VS-2691 &middot; continuous campaign &middot; no batch windows",
              [PILL_LIVE, pill_status("Ingesting"), pill("Event based")],
              procsvg(nodes, width=880) + mbal([
                  ("Evidence sources", "6", 0, ""),
                  ("Integrity", "99.2", 1, "%"),
                  ("Continuity", "98.6", 1, "%"),
                  ("Trust score", "87.4", 1, ""),
              ]),
              "Inputs &middot; physical &middot; legal &middot; documentary &middot; operational",
              "Result &middot; a living digital twin",
              states="Ingesting|Verifying|Custodied")

    b = [phead("How it works", "How it works",
               "Continuous verification, not point in time audits.",
               "Verysset transforms static verification into a continuous, measurable and traceable process, "
               "giving rise to a real time verifiable digital twin of the asset.")]

    b.append('<section class="sec"><div class="wrap">')
    b.append('<div class="steps">'
             '<div class="step rv" data-i="0"><span class="sn">Step 01</span><h3>Structured ingestion</h3>'
             '<p>Physical, legal and documentary evidence associated with the asset is ingested continuously.</p></div>'
             '<div class="step rv" data-i="1"><span class="sn">Step 02</span><h3>Continuous verification</h3>'
             '<p>Data integrity and coherence are verified persistently over time.</p></div>'
             '<div class="step rv" data-i="2"><span class="sn">Step 03</span><h3>Custody &amp; scoring</h3>'
             '<p>A verifiable asset history is custodied with a dynamic trust score.</p></div></div>')
    b.append('<div class="res rv"><span class="k">Result</span><p>A living digital twin of the asset, continuously updated, '
             'that remains observable, auditable and governable throughout its operational lifecycle.</p></div>')
    b.append('<div class="mt rv">' + p + '</div>')
    b.append('</div></section>')

    b.append('<section class="sec alt"><div class="wrap"><div class="g2b">')
    b.append('<div class="rv"><span class="eb">The verifiable digital twin</span>'
             '<h2 class="t w">The asset, mirrored by its own evidence.</h2>'
             '<p class="lede">Every verified event updates the twin. Nothing is re-declared, nothing waits for the next audit '
             'window, and every state the asset has ever been in remains reconstructable.</p>'
             '<div class="mt2"><a class="tl" href="engines.html">See the engines behind it <span class="ar">&rarr;</span></a></div></div>')
    # looping digital twin (mirror.py), replaces the static twin.webp
    b.append('<div class="rv" data-i="1">' + mirror.figure() + '</div>')
    b.append('</div></div></section>')

    b.append('<section class="sec" id="services"><div class="wrap">')
    b.append('<div class="head-split"><div class="rv"><span class="eb">Core Verysset services</span>'
             '<h2 class="t">An integrated stack of sovereign infrastructure.</h2></div>'
             '<div class="rv" data-i="1"><p class="lede" style="margin-top:0">Continuous verification, evidence custody, and '
             'institutional interoperability of real world assets.</p></div></div>')
    b.append('<div class="slist mt">')
    for i, (n, h, p2) in enumerate(SERVICES):
        b.append('<div class="s%s rv" data-i="%d"><span class="sn">%s</span><h4>%s</h4><p>%s</p></div>'
                 % (" lead" if i == 0 else "", min(i, 6), n, h, p2))
    b.append('</div></div></section>')

    b.append(cta("From static snapshots to live, measurable trust.",
                 "Bring one asset class into continuous verification and measure the difference against your current audit cycle."))

    return page("how-it-works.html",
                "How it works | Verysset",
                "Structured ingestion, continuous verification and custody with a dynamic trust score. The Verysset verification line, step by step.",
                "".join(b), prev=("index.html", "Home"), nxt=("engines.html", "Engines"))


def build_engines():
    nodes = [
        {"t": "GEO SENTINEL", "s": "place &middot; time &middot; condition", "icon": "geo"},
        {"t": "AURA",         "s": "integrity &middot; coherence",           "icon": "aura"},
        {"t": "PEDIGREE",     "s": "lineage &middot; trust score",           "icon": "ledger"},
    ]
    p = panel("ENGINE LINE &middot; GEO / AURA / PEDIGREE",
              "asset VS-2691 &middot; campaign 04 &middot; 3 engines gated",
              [PILL_LIVE, pill_status("Capturing"), pill("Continuous")],
              procsvg(nodes, width=880) + mbal([
                  ("Events captured", "100", 0, "%"),
                  ("Integrity passed", "99.2", 1, "%"),
                  ("Lineage complete", "98.6", 1, "%"),
                  ("Trust score", "87.4", 1, ""),
              ]),
              "Engine feed &middot; sensors &middot; registries &middot; operations &middot; counterparties",
              "Evidence balance conserved at every stage",
              states="Capturing|Verifying|Scored")

    b = [phead("Engines", "Core technologies",
               "Three engines. One verifiable truth.",
               "Technology in service of institutional control, not speculation. Each engine does one job and hands "
               "its output to the next, so the evidence balance is conserved at every stage.")]

    b.append('<section class="sec"><div class="wrap"><div class="rv">' + p + '</div></div></section>')

    b.append('<section class="sec alt"><div class="wrap">')
    for i, (n, ic, name, desc, img, alt, bullets) in enumerate(ENGINES):
        rowcls = "g2b" if i % 2 == 0 else "g2b"
        b.append('<div class="%s" style="margin-bottom:clamp(44px,5vw,76px)">' % rowcls)
        b.append('<div class="rv"><span class="eb">Engine %s</span><h2 class="t w">%s</h2><p class="lede">%s</p>'
                 '<div class="vgrid" style="grid-template-columns:1fr 1fr;margin-top:28px">' % (n, name, desc))
        for bl in bullets:
            b.append('<div class="v"><div class="vm"></div><h4>%s</h4></div>' % bl)
        b.append('</div></div>')
        # round 8: looping dark 3D engine illustration (engines_anim.py), static image only as a fallback
        fig = engines_anim.figure(ic)
        if fig:
            b.append('<div class="rv" data-i="1">' + fig + '</div>')
        else:
            b.append('<div class="rv" data-i="1"><div class="eshot" style="margin-top:0">'
                     '<img src="assets/%s" alt="%s" style="display:block;width:100%%;height:auto" loading="lazy" decoding="async"></div></div>' % (img, alt))
        b.append('</div>')
    b.append('</div></section>')

    b.append('<section class="sec"><div class="wrap">')
    b.append('<div class="ctr rv" style="max-width:760px;margin:0 auto"><span class="eb nb">Together</span>'
             '<h2 class="t">Capture, verify, remember.</h2>'
             '<p class="lede">Geo Sentinel establishes what happened and where. Aura decides whether the record holds. '
             'Pedigree keeps the whole history and turns it into a score an institution can act on.</p></div>')
    b.append(engines_cards())
    b.append('</div></section>')

    b.append(cta("Put the three engines on your asset class.",
                 "Institutional evaluation runs in a controlled environment, with functional separation preserved end to end."))

    return page("engines.html",
                "Engines | Verysset",
                "Geo Sentinel, the Aura Verification Engine and the Pedigree Engine: capture, verify and remember the evidence behind a real world asset.",
                "".join(b), prev=("how-it-works.html", "How it works"), nxt=("institutions.html", "Institutions"))


def build_institutions():
    b = [phead("Institutions", "Institutional validation",
               "Aligned to the standards institutions require.",
               "Operational validation, functional separation and interoperability standards: the conditions under which "
               "regulated institutions can adopt a verification layer.")]

    b.append('<section class="sec"><div class="wrap">')
    b.append('<div class="rv"><span class="eb">Validation criteria</span><h2 class="t">Six conditions, all non negotiable.</h2></div>')
    b.append(vgrid())
    b.append('</div></section>')

    # Institutions & actors: continuous verification, Big 4 audit, data pedigree, Trust Score bands
    b.append('<section class="sec alt" id="actors"><div class="wrap">')
    b.append('<div class="head-split"><div class="rv"><span class="eb">Sovereign-grade infrastructure</span>'
             '<h2 class="t">Institutions &amp; actors</h2></div>'
             '<div class="rv" data-i="1"><p class="ia-lead">Continuous verification of real-world assets, audited end to end.</p>'
             '<p class="lede">Every asset is cross-validated against 100+ verification modes, from satellite and SAR radar '
             'to IoT sensors and public registries. Every digital twin is independently audited by the Big 4 '
             '(Deloitte, PwC, EY, KPMG) in its first year after launch, reaches 99.9% replica accuracy across 9 twin layers, '
             'and carries a 6-stage data pedigree from source capture to DLT registration.</p></div></div>')

    b.append('<ul class="chips c4 rv" data-i="2" aria-label="Verification metrics: 100+ verification modes, '
             '99.9% replica accuracy, 9 twin layers, 6-stage data pedigree">')
    for ic, num, lab, cap in IA_STATS:
        b.append('<li class="chip"><span class="cib">%s</span><div class="cbd"><b><bdi dir="ltr">%s</bdi></b>'
                 '<span class="cl">%s</span><p class="cc">%s</p></div></li>' % (STAT_ICONS[ic], num, lab, cap))
    b.append('</ul>')

    b.append('<div class="ia-grid">')
    b.append('<div class="ia-card rv"><span class="eb">Independent audit</span>'
             '<h3 class="t3">Audited by the Big 4 in the first year after launch.</h3>'
             '<ul class="ia-aud" aria-label="Big 4 auditors: Deloitte, PwC, EY, KPMG">' +
             "".join('<li lang="en" dir="ltr" data-noi18n>%s</li>' % a for a in AUDITORS) + '</ul>'
             '<p class="ia-cap">Every digital twin independently audited in its first year after launch.</p>'
             '<p class="ia-note">Plus specialized firms per vertical. Mandatory by design.</p></div>')
    # looping data pedigree packet flow (pedigree.py): rail above the list, badges pulse in step
    ped_svg, ped_badges = pedigree.build()
    b.append('<div class="ia-card rv" data-i="1" data-loop><span class="eb">Data pedigree</span>'
             '<h3 class="t3">Six stages, from source to ledger.</h3>' + ped_svg + '<ol class="ia-ped">' +
             "".join('<li><span class="ia-pn %s">%s</span><span class="ia-pt">%s</span></li>' % (ped_badges[i], st[0], st[1])
                     for i, st in enumerate(PEDIGREE)) +
             '</ol></div>')
    b.append('</div>')

    b.append('<div class="ia-card ia-trust rv">'
             '<div class="ia-th"><div><span class="eb">Trust Score</span>'
             '<h3 class="t3">One continuous score, from 0 to 100.</h3></div>'
             '<p>The Aura Verification Engine ingests and cross-validates 100+ sources to produce a continuous Trust Score.</p></div>'
             '<ol class="ia-band" aria-label="Trust Score bands, lowest to highest">' +
             "".join('<li class="b-%s"><span class="ia-bar" aria-hidden="true"></span><span class="ia-bn">%s</span>'
                     '<bdi class="ia-br" dir="ltr">%s</bdi></li>' % t for t in TRUST_BANDS) +
             '</ol>' + verify_modes_block() + '</div>')
    # animated digital twin, its own module below the Trust Score card (twin.py)
    b.append(twin.module())
    b.append('</div></section>')

    b.append('<section class="sec"><div class="wrap"><div class="g2b">')
    b.append('<div class="rv"><span class="eb">Jurisdiction ready</span><h2 class="t w">Evidence that survives a supervisor.</h2>'
             '<p class="lede">Continuous records, functional separation and reconstructable history are what let a regulated '
             'entity adopt a verification layer without inheriting a new counterparty risk.</p>'
             '<div class="mt2"><a class="tl" href="compliance.html">Read the compliance position <span class="ar">&rarr;</span></a></div></div>')
    # looping evidence stream (jurisdiction.py), replaces the static jurisdiction.webp
    b.append('<div class="rv" data-i="1">' + jurisdiction.figure() + '</div>')
    b.append('</div></div></section>')

    b.append(cta("Start a formal institutional evaluation.",
                 "Evaluation runs on real assets, under your control standards, with structured reporting under NDA."))

    return page("institutions.html",
                "Institutions | Verysset",
                "Institutional validation criteria, Big 4 audited digital twins, a 6-stage data pedigree and the continuous Trust Score for real world assets.",
                "".join(b), prev=("engines.html", "Engines"), nxt=("markets.html", "Markets"))


def build_markets():
    b = [phead("Markets", "Verysset markets",
               "Built for every institutional mandate.",
               "One verification infrastructure, applied across every class of institutional capital. "
               "Select a mandate to see how it fits.")]

    b.append('<section class="sec"><div class="wrap"><div class="mk">')
    b.append('<div class="mlist rv" role="tablist" aria-label="Institutional mandates"><span class="mind" aria-hidden="true"></span>')
    for i, (n, t, dsc) in enumerate(MARKETS):
        i18n_reg(t, "markets.html"); i18n_reg(dsc, "markets.html")
        b.append('<button class="mb%s" role="tab" id="mkb%d" aria-selected="%s" aria-controls="mk-panel" '
                 'data-n="%s" data-t="%s" data-d="%s" data-stats="%s">'
                 '<span class="mi">%s</span>%s<span class="mbt">%s</span></button>'
                 % (" lead" if i == 0 else "", i, "true" if i == 0 else "false", n, t, dsc, market_stats_attr(i),
                    n, market_icon(i), t))
    b.append('</div>')
    b.append('<div class="mpan rv" data-i="1" id="mk-panel" role="tabpanel" aria-live="polite">'
             '<div><span class="mkic" id="mk-ic" aria-hidden="true">%s</span>'
             '<span class="mk-eb">Mandate focus</span><h3 id="mk-t">%s</h3><p id="mk-p">%s</p>'
             '<div class="mstats" id="mk-s">%s</div></div>'
             '<div class="mfoot"><i></i><span id="mk-i">Mandate 01 / 12</span></div></div>'
             % (market_icon(0, "mic big"), MARKETS[0][1], MARKETS[0][2], market_stats_html(0)))
    b.append('</div></div></section>')

    b.append('<section class="sec alt"><div class="wrap">')
    b.append('<div class="rv"><span class="eb">All mandates</span><h2 class="t">Twelve markets, one evidence standard.</h2></div>')
    b.append('<div class="g3 mt">')
    for i, (n, t, dsc) in enumerate(MARKETS):
        if i == 0:
            # the lead mandate (RWA & Tokenization): a 2x2 near-black card that also carries its stat blocks
            b.append('<div class="card lead rv"><div class="lead-h"><span class="mkic sm" aria-hidden="true">%s</span>'
                     '<span class="kn mono">Mandate %s</span><h3>%s</h3><p>%s</p></div>'
                     '<div class="mstats">%s</div></div>' % (market_icon(i), n, t, dsc, market_stats_html(i)))
            continue
        b.append('<div class="card rv" data-i="%d"><div class="rule"></div>'
                 '<span class="mkic sm" aria-hidden="true">%s</span>'
                 '<span class="kn mono" style="font-size:10.5px;letter-spacing:.14em;color:var(--faint)">Mandate %s</span>'
                 '<h3 style="margin-top:10px">%s</h3><p>%s</p></div>' % (i % 3, market_icon(i), n, t, dsc))
    b.append('</div></div></section>')

    b.append(cta("Which mandate are you verifying?",
                 "Bring the asset class, the counterparties and the reporting obligation. We will map the verification line to it."))

    return page("markets.html",
                "Markets | Verysset",
                "Twelve institutional mandates covered by one verification infrastructure, from carbon credits to transport and mobility.",
                "".join(b), prev=("institutions.html", "Institutions"), nxt=("tokenization.html", "Tokenization"))


def build_tokenization():
    nodes = [
        {"t": "INGEST",  "s": "evidence verified",     "icon": "ingest"},
        {"t": "SCORE",   "s": "pedigree engine",       "icon": "score"},
        {"t": "ANCHOR",  "s": "smart contract link",   "icon": "token"},
    ]
    big = panel("TOKENIZATION PLANT &middot; INGEST / SCORE / ANCHOR",
                "lot VS-2691 &middot; campaign feed 15,300 evidence units &middot; 3 stages gated",
                [PILL_LIVE, pill_status("Ingesting"), pill("ERC 3643"), pill("Polymesh")],
                procsvg(nodes, width=980) + mbal([
                    ("Evidence accepted", "100", 0, "%"),
                    ("Integrity", "99.2", 1, "%"),
                    ("Continuity", "98.6", 1, "%"),
                    ("Trust score", "87.4", 1, ""),
                    ("Anchor confirmed", "100", 0, "%"),
                ]),
                "Sources &middot; field evidence &middot; legal registry &middot; operations ledger &middot; counterparty attestations",
                "Evidence balance conserved &middot; variance within tolerance",
                states="Ingesting|Scoring|Anchored")

    full = [
        {"t": "EVIDENCE", "s": "field &middot; legal",       "icon": "doc"},
        {"t": "GEO",      "s": "place &middot; time",        "icon": "geo"},
        {"t": "AURA",     "s": "integrity",                  "icon": "aura"},
        {"t": "PEDIGREE", "s": "lineage custody",            "icon": "ledger"},
        {"t": "SCORE",    "s": "dynamic trust",              "icon": "score"},
        {"t": "TOKEN",    "s": "instrument mint",            "icon": "token"},
        {"t": "MARKET",   "s": "institutional venue",        "icon": "globe"},
    ]
    chain = panel("ANCHORING CHAIN &middot; EVIDENCE TO INSTRUMENT",
                  "twin VS-2691 &middot; 7 hops &middot; chain agnostic",
                  [PILL_LIVE, pill_status("Linked"), pill("Chain agnostic")],
                  procsvg(full, width=1160) + mbal([
                      ("Hops verified", "7", 0, ""),
                      ("Lineage retained", "100", 0, "%"),
                      ("Score at mint", "87.4", 1, ""),
                      ("Reconstructable", "100", 0, "%"),
                  ]),
                  "Verification is independent of any single chain",
                  "Polymesh &middot; Asentrix &middot; ERC 3643",
                  states="Linking|Scoring|Minting|Linked")

    b = [phead("Tokenization", "RWA &amp; tokenization model",
               "Tokenization anchored to observable truth.",
               "Verysset acts as the sovereign verification layer anchoring tokenized assets to a verifiable digital twin "
               "of the real world asset, continuously fed by validated evidence. Tokenization is based on measurable, "
               "observable, real time trust, not static declarations.")]

    b.append('<section class="sec"><div class="wrap"><div class="rv">' + big + '</div>')
    b.append('<div class="g3 mt">'
             '<div class="card rv" data-i="0"><div class="rule"></div><h3>01 &middot; Ingest</h3>'
             '<p>Physical, legal and operational evidence is verified continuously.</p></div>'
             '<div class="card rv" data-i="1"><div class="rule"></div><h3>02 &middot; Score</h3>'
             '<p>The dynamic trust score is computed via the Pedigree Engine.</p></div>'
             '<div class="card rv" data-i="2"><div class="rule"></div><h3>03 &middot; Anchor</h3>'
             '<p>The trust score links to smart contracts, digital instruments and validation.</p></div></div>')
    b.append('</div></section>')

    b.append('<section class="sec alt"><div class="wrap">')
    b.append('<div class="head-split"><div class="rv"><span class="eb">Anchoring chain</span>'
             '<h2 class="t">From field evidence to a minted instrument.</h2></div>'
             '<div class="rv" data-i="1"><p class="lede" style="margin-top:0">Every hop is verified and retained. '
             'The instrument carries the score it was minted against, and the whole lineage stays reconstructable '
             'long after settlement.</p></div></div>')
    b.append('<div class="mt rv">' + chain + '</div>')
    b.append('</div></section>')

    b.append('<section class="sec"><div class="wrap"><div class="g2b">')
    b.append('<div class="rv"><span class="eb">What anchoring is not</span><h2 class="t w">Verysset never touches the instrument.</h2>'
             '<p class="lede">The verification layer publishes evidence and a score. Issuance, custody, pricing and settlement '
             'stay entirely with the regulated entities that already perform them.</p>'
             '<div class="mt2"><a class="tl" href="compliance.html">Read the neutrality position <span class="ar">&rarr;</span></a></div></div>')
    b.append('<div class="rv" data-i="1"><div class="g2" style="gap:16px">')
    for i, (h, p2) in enumerate(NOCARDS):
        b.append('<div class="no"><span class="nx" aria-hidden="true">NO</span><h4>%s</h4><p>%s</p></div>' % (h, p2))
    b.append('</div></div></div></div></section>')

    b.append(cta("Anchor your instrument to evidence that updates itself.",
                 "Mint against verifiable truth, not static declarations, and keep the lineage available to every counterparty."))

    return page("tokenization.html",
                "Tokenization | Verysset",
                "Ingest, score and anchor. The Verysset tokenization line links digital instruments to a continuously verified digital twin.",
                "".join(b), prev=("markets.html", "Markets"), nxt=("compliance.html", "Compliance"))


def build_compliance():
    b = [phead("Compliance", "Legal &amp; governance",
               "Neutral by design.",
               "Verysset operates as a sovereign, neutral verification infrastructure, built to integrate with financial "
               "and regulatory systems without assuming intermediation roles.")]

    b.append('<section class="sec" id="legal"><div class="wrap">')
    b.append('<div class="rv"><span class="eb">Four hard limits</span><h2 class="t">What Verysset does not do.</h2></div>')
    b.append('<div class="g4 mt">')
    for i, (h, p2) in enumerate(NOCARDS):
        b.append('<div class="no rv" data-i="%d"><span class="nx" aria-hidden="true">NO</span><h4>%s</h4><p>%s</p></div>' % (i, h, p2))
    b.append('</div>')
    b.append('<p class="neu rv">Verysset does not custody funds, issue instruments, trade or assume fiduciary risk. '
             'It is a verification and evidence custody layer, neutral to counterparties, chains and jurisdictions by design.</p>')
    b.append('</div></section>')

    # Dubai skyline backdrop behind the incorporation block (skyline.py, decorative, aria-hidden)
    b.append('<section class="sec alt skysec" id="jurisdiction">' + skyline.svg() + '<div class="wrap"><div class="g2b">')
    b.append('<div class="rv"><span class="eb">Jurisdiction</span><h2 class="t w">Dubai incorporated. Jurisdiction agnostic.</h2>'
             '<div class="frames"><span class="fr">MiCA (EU)</span><span class="fr">MAS (Singapore)</span>'
             '<span class="fr">VARA (Dubai)</span><span class="fr">FATF</span><span class="fr">ISO 20022</span></div></div>')
    b.append('<div class="rv" data-i="1"><p class="lede" style="margin-top:6px">Verysset is incorporated in Dubai, '
             'United Arab Emirates, and operates under a jurisdiction agnostic model designed to integrate with diverse '
             'regulatory environments without assuming regulated functions.</p>'
             '<p class="lede">Designed to coexist with frameworks such as <strong>MiCA (EU), MAS (Singapore), VARA (Dubai)</strong> '
             'and applicable US regulations, without replacing the obligations of user entities.</p>'
             '<hr class="hr" style="margin:28px 0 22px">'
             '<p class="addr"><b>Verysset Veritas Ledger Ltd.</b>Innovation Hub, Level 14, Gate Village Building 4<br>'
             'Dubai International Financial Centre (DIFC)<br>Dubai, United Arab Emirates</p></div>')
    b.append('</div></div></section>')

    b.append('<section class="sec" id="licensing"><div class="wrap">')
    b.append('<div class="ctr rv" style="max-width:820px;margin:0 auto"><span class="eb nb">Licensing program</span>'
             '<h2 class="t">Empowering sovereigns &amp; institutions.</h2>'
             '<p class="lede">At VERYSSET, we empower nations and institutions to operate their own tokenization ecosystems '
             'under a proven sovereign framework.</p></div>')
    b.append('<div class="g2b mt" id="governance">')
    b.append('<div class="rv"><h2 class="t w" style="font-size:clamp(24px,3vw,38px);margin-top:0">Governance</h2>'
             '<p class="lede">Verysset&rsquo;s governance ensures neutrality, control and sustainable institutional adoption, '
             'built on clear separation of functions, structured institutional reporting under NDA, and traceability and '
             'auditability by design.</p></div>')
    b.append('<div class="vgrid rv" data-i="1" style="grid-template-columns:1fr">'
             '<div class="v"><div class="vm"></div><h4>Clear separation of functions</h4>'
             '<p>Verification, custody, financial operation and supervision remain structurally distinct.</p></div>'
             '<div class="v"><div class="vm"></div><h4>Institutional reporting under NDA</h4>'
             '<p>Structured reporting to institutional counterparties under confidentiality.</p></div>'
             '<div class="v"><div class="vm"></div><h4>Traceability &amp; auditability by design</h4>'
             '<p>Every event, state and change remains reconstructable end to end.</p></div></div>')
    b.append('</div></div></section>')

    b.append(cta("Operate a sovereign verification framework.",
                 "Licensing lets a nation or institution run its own tokenization ecosystem on a proven, neutral framework."))

    return page("compliance.html",
                "Compliance &amp; DIFC | Verysset",
                "Neutral by design: no custody, no issuance, no trading, no fiduciary risk. DIFC incorporated and aligned with MiCA, MAS, VARA and FATF.",
                "".join(b), prev=("tokenization.html", "Tokenization"), nxt=("faq.html", "FAQ"))


def build_faq():
    b = [phead("FAQ", "FAQ", "Answers, plainly.",
               "The questions institutional teams ask first, answered without hedging.")]
    b.append('<section class="sec"><div class="wrap">')
    b.append(faq_block())
    b.append('</div></section>')
    b.append(cta("Still have a question?",
                 "Send it with your asset class and we will answer it against your actual verification obligation.",
                 "Ask the institutional team"))
    return page("faq.html", "FAQ | Verysset",
                "Trust score, jurisdiction, neutrality, chains and privacy: the Verysset questions institutional teams ask first.",
                "".join(b), prev=("compliance.html", "Compliance"), nxt=("partners.html", "Partners"))


def build_partners():
    b = [phead("Partners", "Trusted allies", "Our partners.",
               "Institutional grade infrastructure, backed by leaders across exchanges, tokenization, capital, "
               "fund administration, earth observation, industrial sensing and audit.")]
    b.append('<section class="sec"><div class="wrap">')
    b.append(partner_grid())
    b.append('<p class="lede rv" style="margin-top:30px">Each partner operates in its own regulated lane. '
             'Verysset supplies the verification layer they anchor to, and never the intermediation.</p>')
    b.append('</div></section>')
    b.append('<section class="sec alt"><div class="wrap"><div class="g4 plane">')
    for i, (kn, t, p2) in enumerate([
        ("Exchanges &amp; venues", "Verified listings", "Venues anchor listed instruments to a live twin instead of a filing."),
        ("Tokenization platforms", "Mint against truth", "Platforms mint against a score, not a declaration, and keep the lineage."),
        ("Capital &amp; administration", "Lower reconciliation", "Administrators cut exception handling by reading one continuous record."),
        ("Sensing, imagery &amp; audit", "Evidence at the source", "Earth observation, sensing and audit leaders strengthen the evidence behind every verified twin."),
    ]):
        b.append('<div class="card rv" data-i="%d"><div class="rule"></div>'
                 '<span class="mono" style="font-size:10.5px;letter-spacing:.14em;color:var(--faint);text-transform:uppercase">%s</span>'
                 '<h3 style="margin-top:10px">%s</h3><p>%s</p></div>' % (i, kn, t, p2))
    b.append('</div></div></section>')
    b.append(cta("Become a Verysset partner.",
                 "If you operate a venue, a platform or an administration stack, the verification layer plugs in behind it."))
    return page("partners.html", "Partners | Verysset",
                "Institutional grade infrastructure backed by leaders across exchanges, tokenization, capital, fund administration, earth observation, industrial sensing and audit.",
                "".join(b), prev=("faq.html", "FAQ"), nxt=("contact.html", "Contact"))


def build_contact():
    b = [phead("Contact", "Request institutional meeting",
               "Operate real world assets under continuous verification.",
               "If your institution needs to operate real world assets under continuous verification and clear trust "
               "metrics, Verysset provides the sovereign infrastructure to do so with control and confidence.")]
    b.append('<section class="sec"><div class="wrap"><div class="g2b">')
    b.append('<div class="rv"><span class="eb">What to expect</span><h2 class="t w">A short, technical first call.</h2>'
             '<p class="lede">Bring the asset class, the counterparties and the reporting obligation. We map the verification '
             'line to it, show the evidence the engines would collect, and agree the scope of a controlled evaluation.</p>'
             '<hr class="hr" style="margin:30px 0 24px">'
             '<p class="addr"><b>Verysset Veritas Ledger Ltd.</b>Innovation Hub, Level 14, Gate Village Building 4<br>'
             'Dubai International Financial Centre (DIFC)<br>Dubai, United Arab Emirates</p>'
             '<p class="addr" style="margin-top:20px"><b>Group entities</b>Verysset Veritas Ledger Ltd. (Dubai, DIFC)</p>'
             '<p class="addr" style="margin-top:20px"><b>Direct</b>'
             '<a class="mailto" href="mailto:%s">%s</a></p></div>' % (CONTACT_EMAIL, CONTACT_EMAIL))
    b.append('<form class="form rv" data-i="1" id="rf" novalidate method="post" '
             'action="mailto:%s" enctype="text/plain" data-mailto="%s">' % (CONTACT_EMAIL, CONTACT_EMAIL) +
             '<div class="fld"><label for="i-fn">Full name</label>'
             '<input id="i-fn" name="fn" type="text" placeholder="Your name" required autocomplete="name"></div>'
             '<div class="fld"><label for="i-in">Institution</label>'
             '<input id="i-in" name="inst" type="text" placeholder="Organization" autocomplete="organization"></div>'
             '<div class="fld"><label for="i-em">Work email</label>'
             '<input id="i-em" name="email" type="email" placeholder="name@institution.com" required autocomplete="email"></div>'
             '<div class="fld"><label for="i-ro">Role</label>'
             '<input id="i-ro" name="role" type="text" placeholder="Title / function" autocomplete="organization-title"></div>'
             '<div class="fld full"><label for="i-ms">Message</label>'
             '<textarea id="i-ms" name="msg" placeholder="Tell us about your asset class and verification needs"></textarea></div>'
             '<div class="fld full"><button type="submit" class="btn" style="width:100%">Request meeting '
             '<span aria-hidden="true">&rarr;</span></button></div>'
             '<div class="note" id="nt"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 12.5 5 5 11-11"/></svg>'
             '<span>Thank you, our institutional team will contact you.</span></div></form>')
    b.append('</div></div></section>')
    b.append('<section class="sec alt"><div class="wrap"><div class="g3">')
    for i, (kn, t, p2, href) in enumerate([
        ("Before the call", "How it works", "The three step verification line and the full service stack.", "how-it-works.html"),
        ("Technical detail", "The engines", "What Geo Sentinel, Aura and Pedigree each produce.", "engines.html"),
        ("Legal position", "Compliance", "Neutrality, DIFC incorporation and regulatory alignment.", "compliance.html"),
    ]):
        b.append('<a class="kcard rv" data-i="%d" href="%s"><span class="kn">%s</span><h3>%s</h3><p>%s</p>'
                 '<span class="go">Open <span>&rarr;</span></span></a>' % (i, href, kn, t, p2))
    b.append('</div></div></section>')
    return page("contact.html", "Contact | Verysset",
                "Request an institutional meeting with Verysset. DIFC incorporated, jurisdiction agnostic verification infrastructure.",
                "".join(b), prev=("partners.html", "Partners"), nxt=("index.html", "Home"))


# ---------------------------------------------------------------- logo review page
# logo.html is the design review page for the identity. It is built with the same head, header,
# footer and i18n wiring as every other page, but it is deliberately NOT in NAV and is noindex.
def _svg_paths(rel):
    return re.findall(r"<path [^>]*/>", open(os.path.join(OUT, rel), encoding="utf-8").read())


def build_logo():
    lw, lh = LOGO["lockup_w"], LOGO["lockup_h"]
    fm = logogen.fmt

    def lock(src, h, alt, cls=""):
        return ('<img%s src="%s" alt="%s" width="%d" height="%d" decoding="async">'
                % (' class="%s"' % cls if cls else "", src, alt, round(h * lw / lh), h))

    def sym(src, s, alt="VERYSSET symbol"):
        return '<img src="%s" alt="%s" width="%d" height="%d" decoding="async">' % (src, alt, s, s)

    def hd(n, eb, h2, p):
        return ('<div class="lghd"><div><span class="eb">%s</span><h2>%s</h2></div><p>%s</p></div>'
                % (eb, h2, p))

    b = [phead("Brand identity", "Design review", "The VERYSSET mark.",
               "A flat yellow circle carrying three nested isometric cubes, and a tracked black wordmark. The "
               "cubes are the real asset inside its verification layers: an open outer frame, solid faces and a "
               "solid core. The name is centered on the circle, so symbol and wordmark share one axis.",
               '<div class="lgmeta"><span class="lgtag y">Design review</span>'
               '<span class="lgtag">Not in public navigation</span>'
               '<span class="lgtag">Flat, four colors</span></div>')]

    # 01 primary lockup
    b.append('<section class="sec tight"><div class="wrap">' +
             hd("01", "01 Primary lockup", "Circle, cubes, wordmark. Nothing else.",
                "The primary mark for every light surface. Solid yellow circle, ink cubes, ink wordmark, "
                "no gradient, no stroke, no effect.") +
             '<figure class="lgplate">' + lock("assets/logo.svg", 120, "VERYSSET primary logo on white", "lgbig") +
             '<figcaption><span>Primary, on white</span><span data-noi18n>assets/logo.svg</span></figcaption></figure>'
             '<figure class="lgplate dk">' + lock("assets/logo-dark.svg", 120, "VERYSSET logo reversed on ink", "lgbig") +
             '<figcaption><span>Reversed, on ink</span><span data-noi18n>assets/logo-dark.svg</span></figcaption></figure>'
             '</div></section>')

    # 02 size ladder
    def ladder(src, dk):
        rows = "".join('<div class="lgrow"><b data-noi18n>%d px</b>%s</div>'
                       % (s, lock(src, s, "VERYSSET logo at %d pixels" % s)) for s in (24, 48, 96))
        return '<div class="lgcol%s">%s</div>' % (" dk" if dk else "", rows)

    b.append('<section class="sec tight alt"><div class="wrap">' +
             hd("02", "02 Size ladder", "Holds its shape from 24 to 240 pixels.",
                "The frame stays open and the core stays legible at header size. At 240 pixels the nested "
                "cubes become the signature.") +
             '<div class="lgladder">' + ladder("assets/logo.svg", False) + ladder("assets/logo-dark.svg", True) +
             '</div><div class="lgcrops">'
             '<figure class="lgcrop">' + lock("assets/logo.svg", 240, "VERYSSET logo at 240 pixels, detail") +
             '<figcaption><span data-noi18n>240 px</span><span>Detail crop</span></figcaption></figure>'
             '<figure class="lgcrop dk">' + lock("assets/logo-dark.svg", 240, "VERYSSET reversed logo at 240 pixels, detail") +
             '<figcaption><span data-noi18n>240 px</span><span>Detail crop</span></figcaption></figure>'
             '</div></div></section>')

    # 03 symbol and favicon
    def symrow(dk):
        cells = "".join('<figure>%s<figcaption data-noi18n>%d</figcaption></figure>'
                        % (sym("assets/logo-symbol.svg", s), s) for s in (96, 48, 24, 16))
        return '<div class="lgsrow%s">%s</div>' % (" dk" if dk else "", cells)

    def tab(dk):
        return ('<div class="lgtabbar%s"><div class="lgtab"><img src="%s" alt="" width="16" height="16">'
                '<span>VERYSSET | Continuous verification</span><i aria-hidden="true"></i></div></div>'
                % (" dk" if dk else "", FAVICON))

    b.append('<section class="sec tight"><div class="wrap">' +
             hd("03", "03 Symbol and favicon", "The circle alone, down to 16 pixels.",
                "For favicon, app icon and avatar. A square viewBox with no padding, so the circle touches its "
                "tile edge to edge. The favicon uses a larger, bolder cut of the same cubes.") +
             '<div class="lgsym"><figure class="lgplate lgsq">' + sym("assets/logo-symbol.svg", 240) +
             '<figcaption><span>Symbol, 240 px</span><span data-noi18n>assets/logo-symbol.svg</span></figcaption></figure>'
             '<div class="lgsyms">' + symrow(False) + symrow(True) +
             '<div class="lgtabs"><span class="lgcap">Current favicon, as the browser tab shows it</span>' +
             tab(False) + tab(True) + '</div></div></div></div></section>')

    # 04 construction (circle lockup: circle D, gap, caps centered on the circle's horizontal axis)
    W = lw
    D, GP, CAPL, BASE = LOGO["circle"], LOGO["gap"], LOGO["cap_line"], LOGO["baseline"]
    R = D / 2.0
    HR = R * LOGO["mark_ratio"]                       # circumradius of the cube mark
    src_dk = open(os.path.join(OUT, "assets/logo-dark.svg"), encoding="utf-8").read()
    ps = _svg_paths("assets/logo-dark.svg")
    g = re.findall(r"<circle [^>]*/>", src_dk)[:1]
    g += [ps[0], ps[1].replace('fill="#FFFFFF"', 'fill="#FFFFFF" opacity=".92"')]
    g.append('<rect class="cs" x="%s" y="-8" width="%s" height="%s"/>' % (fm(D), fm(GP), fm(D + 16)))
    g.append('<circle class="gl" cx="%s" cy="%s" r="%s"/>' % (fm(R), fm(R), fm(HR)))
    for x in (0, R - HR * 0.8660254, R, R + HR * 0.8660254, D, D + GP):
        g.append('<line class="gl" x1="%s" y1="-30" x2="%s" y2="%s"/>' % (fm(x), fm(x), fm(D + 28)))
    for y, lab, key in ((0, "TOP  0u", False), (CAPL, "CAP LINE  %su" % fm(CAPL), False),
                        (R, "AXIS  %su" % fm(R), True), (BASE, "BASELINE  %su" % fm(BASE), False),
                        (D, "BOTTOM  %su" % fm(D), False)):
        g.append('<line class="gl%s" x1="-40" y1="%s" x2="%s" y2="%s"/>' % (" key" if key else "", fm(y), fm(W + 22), fm(y)))
        g.append('<text x="%s" y="%s"%s>%s</text>' % (fm(W + 30), fm(y + 2.8), ' class="k"' if key else "", lab))
    # dimensions
    g.append('<path class="dm" d="M-20 0V%sM-24 0H-16M-24 %sH-16"/>' % (fm(D), fm(D)))
    g.append('<text x="-30" y="%s" text-anchor="middle" transform="rotate(-90 -30 %s)">%su</text>' % (fm(R), fm(R), fm(D)))
    g.append('<path class="dm" d="M%s -14H%sM%s -18V-10M%s -18V-10"/>' % (fm(D), fm(D + GP), fm(D), fm(D + GP)))
    g.append('<text x="%s" y="-21" text-anchor="middle">%su</text>' % (fm(D + GP / 2.0), fm(GP)))
    g.append('<path class="dm" d="M%s %sH%sM%s %sV%sM%s %sV%s"/>'
             % (fm(D), fm(D + 16), fm(D + GP), fm(D), fm(D + 12), fm(D + 20), fm(D + GP), fm(D + 12), fm(D + 20)))
    g.append('<text x="%s" y="%s" text-anchor="middle">%su CLEAR SPACE</text>' % (fm(D + GP / 2.0), fm(D + 30), fm(GP)))
    g.append('<path class="dm" d="M%s %sV%sM%s %sH%sM%s %sH%s"/>'
             % (fm(W + 12), fm(CAPL), fm(BASE), fm(W + 8), fm(CAPL), fm(W + 16), fm(W + 8), fm(BASE), fm(W + 16)))
    g.append('<text x="%s" y="%s" class="m">%su CAP HEIGHT</text>' % (fm(W + 30), fm((R + BASE) / 2.0 + 2.8), fm(LOGO["cap_height"])))
    vb = "-64 -50 %s 192" % fm(W + 64 + 200)
    rules = [("%su" % fm(D), "Circle", "The ground of the symbol. Solid Verysset yellow, flat, no stroke, no gradient."),
             ("%d%%" % round(LOGO["mark_ratio"] * 100), "Cube mark",
              "Three nested isometric cubes in an exact 30 degree projection, circumscribed at this share of the diameter."),
             ("3", "Nested cubes", "Open outer frame, solid middle faces, solid core. The real asset inside its verification layers."),
             ("%su" % fm(R), "Shared axis", "The center of the circle. The capitals of the name are centered on it, from the cap line to the baseline."),
             ("%su" % fm(GP), "Clear space", "Between symbol and name, and the minimum margin around the lockup.")]
    b.append('<section class="sec ink-band"><div class="wrap">' +
             hd("04", "04 Construction", "One center carries the whole mark.",
                "The circle, the cubes and the capitals share one horizontal axis. The circle is drawn taller than "
                "the caps, because a circle carries less visual mass than a square of the same height.") +
             '<figure class="lgcon"><svg viewBox="%s" role="img" aria-label="Construction grid of the VERYSSET logo" '
             'data-noi18n>%s</svg></figure>' % (vb, "".join(g)) +
             '<ul class="lgrules">' +
             "".join('<li><b data-noi18n>%s</b><h3>%s</h3><p>%s</p></li>' % r for r in rules) +
             '</ul></div></section>')

    # 05 color
    sw = [("#FFD400", "Verysset yellow", "The circle, and the cubes of the single color symbol. Never tinted, never gold."),
          ("#E6BF00", "Deep yellow", "Hover states and fine keylines. Never the mark itself."),
          ("#0A0A09", "Ink", "The cubes inside the circle, and the wordmark on white and light grounds."),
          ("#FFFFFF", "White", "The wordmark on ink and dark imagery.")]
    b.append('<section class="sec tight alt"><div class="wrap">' +
             hd("05", "05 Color", "Four values. No gold, no gradient.",
                "The circle is always #FFD400 on every ground, so the brand never shifts between light and dark.") +
             '<div class="lgswg">' +
             "".join('<div class="lgsw"><i style="background:%s"></i><div><b>%s</b><code data-noi18n>%s</code>'
                     '<p>%s</p></div></div>' % (h, n, h, u) for h, n, u in sw) +
             '</div></div></section>')

    # 06 files
    files = [("assets/logo.svg", "Primary lockup", "Light grounds. Yellow circle, ink cubes and the ink wordmark."),
             ("assets/logo-dark.svg", "Reversed lockup", "Dark grounds. Yellow circle, ink cubes and the white wordmark."),
             ("assets/logo-symbol.svg", "Symbol", "Yellow circle with ink cubes, square viewBox. App icon, avatar and social profile, on light or dark."),
             ("assets/logo-symbol-yellow.svg", "Single color symbol", "Yellow cubes on transparent, for dark and high contrast grounds."),
             ("assets/favicon.svg", "Favicon", "A bolder cut of the symbol, wired as the favicon on every page.")]
    rows = []
    for f, n, d in files:
        prev = sym(f, 40, "") if ("symbol" in f or "favicon" in f) else lock(f, 24, "")
        rows.append('<li><span class="lgfi%s">%s</span><div><b>%s</b><p>%s</p></div>'
                    '<code data-noi18n>%s &middot; %.1f KB</code><a class="btn gh sm" href="%s" download>Download</a></li>'
                    % (" dk" if ("dark" in f or "yellow" in f) else "", prev, n, d, f,
                       os.path.getsize(os.path.join(OUT, f)) / 1024.0, f))
    b.append('<section class="sec tight alt"><div class="wrap">' +
             hd("06", "06 Files", "Self contained vectors, no fonts required.",
                "The wordmark is drawn as outlines, so every file renders the same in any browser, deck or tool.") +
             '<ul class="lgfiles">' + "".join(rows) + '</ul>'
             '<p class="lgnote">Wordmark: Clash Display Semibold, converted to outlines, tracked wide and spaced '
             'optically pair by pair. Every file is generated by one script, <code data-noi18n>logogen.py</code>, '
             'so the geometry is exact in every export. Flat in every file: no gradient, no glow.</p>'
             '</div></section>')

    return page("logo.html", "Logo review | Verysset",
                "Design review of the VERYSSET identity: primary lockup, reversed lockup, symbol, favicon and construction.",
                "".join(b), pgn=False, noindex=True)


if __name__ == "__main__":
    sizes = {}
    sizes["index.html"] = build_index()
    sizes["how-it-works.html"] = build_how()
    sizes["engines.html"] = build_engines()
    sizes["institutions.html"] = build_institutions()
    sizes["markets.html"] = build_markets()
    sizes["tokenization.html"] = build_tokenization()
    sizes["compliance.html"] = build_compliance()
    sizes["faq.html"] = build_faq()
    sizes["partners.html"] = build_partners()
    sizes["contact.html"] = build_contact()
    sizes["logo.html"] = build_logo()        # design review page: built, but NOT in NAV
    for k in sorted(sizes):
        print("%-22s %7.1f KB" % (k, sizes[k] / 1024.0))
    css_loops = loopkit.inject(os.path.join(OUT, "assets", "site.css"))
    for nm, dur, note in loopkit.durations():
        print("loop %-4s %5.2fs  %s" % (nm, dur, note))
    print("loops css block        %7.1f KB" % (css_loops / 1024.0))
    total, full, miss = i18n_report()
    print("-" * 46)
    print("i18n keys              : %d" % total)
    print("fully translated (6/6) : %d" % full)
    print("english fallback       : %d  (see i18n_missing.json)" % miss)
