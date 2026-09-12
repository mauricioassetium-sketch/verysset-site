#!/usr/bin/env python3
# Verysset multi-page static site generator.
# Emits one self-contained HTML file per nav item, all sharing assets/site.css + assets/site.js.
# Rule: no em dash anywhere in the output. Hyphens only.

import os, re, io, json, html, hashlib
import mapgen
import i18n_cat

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

# Favicon = the new Verysset cube mark (vector, crisp at 16px).
FAVICON = "assets/favicon.svg"

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
def head(title, desc, page):
    return """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s</title>
<meta name="description" content="%s">
<meta name="theme-color" content="#ffffff">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="%s">
<link rel="preload" href="assets/fonts/ClashDisplay-Medium.otf" as="font" type="font/otf" crossorigin>
<link rel="preload" href="assets/fonts/ClashDisplay-Semibold.otf" as="font" type="font/otf" crossorigin>
<link rel="preload" href="assets/fonts/Inter-Variable.ttf" as="font" type="font/ttf" crossorigin>
<link rel="stylesheet" href="assets/site.css">
</head><body>
<a class="skip" href="#main">Skip to content</a>
<div class="pbar" aria-hidden="true"></div>
%s
<main id="main">""" % (title, desc, title, desc, FAVICON, navbar(page))


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
<a class="brand" href="index.html" aria-label="Verysset home"><img class="blogo" src="assets/verysset-logo.svg" alt="Verysset" width="178" height="42" decoding="async"></a>
<nav class="nmenu" aria-label="Primary">%s</nav>
<div class="nact">%s<a class="btn sm" href="contact.html">Request a meeting</a>
<button class="burg" id="burg" aria-label="Menu" aria-expanded="false" aria-controls="drawer"><span></span></button></div>
</div><div class="drawer" id="drawer">%s<a class="btn" href="contact.html">Request a meeting</a></div></header>""" % (links, lang_select(), dlinks)


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
# 24x24, stroke based (1.5px, currentColor), the .acf detail carries the #FFD400 accent.
def _svg(cls, title, body):
    return ('<svg class="%s" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            '<title>%s</title>%s</svg>' % (cls, title, body))

STAT_ICONS = {
    "trust": _svg("ci", "Live trust score shield",
                  '<path class="acf" d="M12 3.2l7 2.8v5.3c0 4.3-2.9 7.9-7 9.5-4.1-1.6-7-5.2-7-9.5V6z"/>'
                  '<path d="m8.9 12.1 2.2 2.2 4.1-4.4"/>'),
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
<a class="brand" href="index.html" aria-label="Verysset home"><img class="blogo" src="assets/verysset-logo-dark.svg" alt="Verysset" width="203" height="48" decoding="async"></a>
<div class="fgrid"><div>
<p>Verysset is a sovereign infrastructure for the continuous verification of real world assets.</p>
<p class="ents">Verysset Veritas Ledger Ltd. (Dubai, DIFC)</p>
<p class="ents">Innovation Hub, Level 14, Gate Village Building 4<br>Dubai International Financial Centre (DIFC)<br>Dubai, United Arab Emirates</p></div>
<div class="fcol"><h5>Platform</h5><a href="how-it-works.html">How it works</a><a href="engines.html">Engines</a><a href="how-it-works.html#services">Services</a><a href="markets.html">Markets</a></div>
<div class="fcol"><h5>Institutions</h5><a href="institutions.html">Actors &amp; savings</a><a href="compliance.html#licensing">Licensing</a><a href="compliance.html#governance">Governance</a><a href="faq.html">FAQ</a></div>
<div class="fcol"><h5>Contact</h5><a href="mailto:CONTACT_EMAIL_TOKEN">CONTACT_EMAIL_TOKEN</a><a href="contact.html">Request a meeting</a><a href="compliance.html#jurisdiction">Jurisdiction</a><a href="compliance.html">Legal</a><a href="partners.html">Partners</a></div>
</div>
<div class="fbot"><span class="fcopy">&copy; 2026 VERYSSET. All rights reserved.</span>
<div class="fstd"><span class="fstdl">Standards-aligned infrastructure</span><ul class="fbadges" aria-label="Standards-aligned infrastructure: ISO 20022, ISO 27001, ISO 27002, ISO 22301"><li class="fbadge">BADGE_INTEROP<span>ISO 20022</span><small>aligned</small></li><li class="fbadge">BADGE_LOCK<span>ISO 27001 / 27002</span><small>aligned</small></li><li class="fbadge">BADGE_CONT<span>ISO 22301</span><small>aligned</small></li></ul></div></div>
<div class="fdisc" lang="en" dir="ltr" data-noi18n><p>DISCLAIMER_TOKEN</p></div>
</div></footer>
<button class="ttop" aria-label="Back to top"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5m-7 7 7-7 7 7"/></svg></button>
<script src="assets/site.js"></script>
</body></html>"""


def page(fname, title, desc, body, prev=None, nxt=None, pgn=True):
    doc = head(title, desc, fname) + body
    if pgn:
        doc += '<section class="sec tight">' + pgnav(prev, nxt) + '</section>'
    doc += (FOOT.replace('CONTACT_EMAIL_TOKEN', CONTACT_EMAIL).replace('DISCLAIMER_TOKEN', DISCLAIMER)
            .replace('BADGE_INTEROP', BADGE_ICONS['interop']).replace('BADGE_LOCK', BADGE_ICONS['lock'])
            .replace('BADGE_CONT', BADGE_ICONS['cont']))
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

ACTORS = [
    ("01", "15 to 30%", "Banks &amp; financial institutions", "Cut duplicated due diligence and rework across lending and trade flows."),
    ("02", "15 to 30%", "Regulated markets (carbon, energy, commodities)", "Replace fragmented audits with one continuous compliance record."),
    ("03", "10 to 25%", "Real world asset owners", "Keep assets verified without the cost of repeated inspections."),
    ("04", "20 to 35%", "Issuers of financial &amp; digital instruments (RWA)", "Anchor instruments to evidence that updates itself."),
    ("05", "20 to 35%", "Asset operators &amp; managers", "One live view of every asset instead of periodic reports."),
    ("06", "20 to 45%", "Tokenization platforms &amp; institutional DLTs", "Mint against verifiable truth, not static declarations."),
    ("07", "25 to 40%", "Custodians, fiduciaries &amp; trust companies", "Reduce reconciliation and exception handling."),
    ("08", "15 to 30%", "Auditors, verifiers &amp; compliance firms", "Shift effort from rechecking to higher value assurance."),
    ("09", "30 to 50%", "Regulators &amp; supervisory authorities", "Monitor continuously and act on signal, not lag."),
    ("10", "10 to 25%", "Insurers &amp; reinsurers", "Price risk on current condition, not stale data."),
    ("11", "20 to 40%", "Governments &amp; public agencies", "Turn public assets into continuously auditable records."),
    ("12", "10 to 20%", "Institutional funds &amp; professional investors", "Know the true state of holdings at any moment."),
]

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
    for i, (href, name, f, h, iw, ih) in enumerate(PARTNERS):
        src, real = partner_logo_file(f)
        o.append('<a class="pcell rv" data-i="%d" href="%s" target="_blank" rel="noopener noreferrer" '
                 'title="%s" aria-label="%s">' % (min(i, 6), href, name, name))
        o.append('<span class="pw">')
        o.append('<img class="plogo" src="assets/%s" alt="%s" width="172" height="52" '
                 'loading="lazy" decoding="async">' % (src, name))
        o.append('</span>')
        o.append('<span class="pname">%s</span></a>' % name)
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
    b.append('<h1 class="rv" data-i="1">Sovereign grade verification for <em>real world assets.</em></h1>')
    b.append('<p class="hsub rv" data-i="2">Continuous, auditable trust. The evidence banks and regulators accept. '
             'One verifiable truth layer for institutional capital.</p>')
    b.append('<div class="hcta rv" data-i="3"><a class="btn" href="contact.html">Request institutional meeting</a>'
             '<a class="tl" href="how-it-works.html">See how it works <span class="ar">&rarr;</span></a></div>')
    b.append('<ul class="chips rv" data-i="4" aria-label="Verysset live network metrics: trust score, continuous verification, ISO 20022 interoperability">'
             '<li class="chip"><span class="cib">' + STAT_ICONS["trust"] + '</span><div class="cbd">'
             '<b><span data-count="87.4" data-dec="1">87.4</span></b><span class="cl"><span class="dot"></span>Live trust score</span>'
             '<p class="cc">Network-wide asset trust index, recalculated in real time.</p></div></li>'
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
        ("how-it-works.html", "Platform", "How it works", "Structured ingestion, continuous verification, custody and scoring, plus the full service stack."),
        ("engines.html", "Technology", "The three engines", "Geo Sentinel, the Aura Verification Engine and the Pedigree Engine in detail."),
        ("institutions.html", "Institutions", "Validation and savings", "Institutional validation criteria and twelve actor profiles with expected savings."),
        ("markets.html", "Mandates", "Twelve markets", "One verification infrastructure applied across every class of institutional capital."),
        ("tokenization.html", "RWA", "Tokenization", "Ingest, score and anchor: the process line that links instruments to evidence."),
        ("compliance.html", "Legal", "Compliance and DIFC", "Neutral by design, DIFC incorporated, aligned with MiCA, MAS, VARA and FATF."),
    ]):
        b.append('<a class="kcard rv" data-i="%d" href="%s"><span class="kn">%s</span><h3>%s</h3><p>%s</p>'
                 '<span class="go">Open <span>&rarr;</span></span></a>' % (i % 3, href, kn, t, p))
    b.append('</div></div></section>')

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
    b.append('<div class="rv" data-i="1" style="border:1px solid var(--line);border-radius:3px;overflow:hidden;background:#fff">'
             '<img src="assets/twin.webp" alt="Verifiable digital twin of a real world asset" '
             'style="display:block;width:100%;height:auto" loading="lazy" decoding="async"></div>')
    b.append('</div></div></section>')

    b.append('<section class="sec" id="services"><div class="wrap">')
    b.append('<div class="head-split"><div class="rv"><span class="eb">Core Verysset services</span>'
             '<h2 class="t">An integrated stack of sovereign infrastructure.</h2></div>'
             '<div class="rv" data-i="1"><p class="lede" style="margin-top:0">Continuous verification, evidence custody, and '
             'institutional interoperability of real world assets.</p></div></div>')
    b.append('<div class="slist mt">')
    for i, (n, h, p2) in enumerate(SERVICES):
        b.append('<div class="s rv" data-i="%d"><span class="sn">%s</span><h4>%s</h4><p>%s</p></div>' % (min(i, 6), n, h, p2))
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

    b.append('<section class="sec alt" id="actors"><div class="wrap">')
    b.append('<div class="head-split"><div class="rv"><span class="eb">Institutions &amp; actors</span>'
             '<h2 class="t">Savings by changing the physics of control.</h2></div>'
             '<div class="rv" data-i="1"><p class="lede" style="margin-top:0">From point in time, fragmented, reactive verification '
             'to continuous, auditable, verifiable verification. The numbers reflect less repetitive work, less friction, '
             'less hidden risk.</p></div></div>')
    b.append('<div class="alist mt">')
    for i, (n, pct, h, p2) in enumerate(ACTORS):
        b.append('<div class="a rv" data-i="%d"><span class="an">%s</span><span class="ap"><i>%s</i></span>'
                 '<h4>%s</h4><p>%s</p></div>' % (min(i, 6), n, pct, h, p2))
    b.append('</div>')
    b.append('<p class="lede rv" style="margin-top:28px">Ranges are expected savings on verification related effort once '
             'continuous verification replaces repeated point in time work. They are indicative and confirmed per institution '
             'during evaluation.</p>')
    b.append('</div></section>')

    b.append('<section class="sec"><div class="wrap"><div class="g2b">')
    b.append('<div class="rv"><span class="eb">Jurisdiction ready</span><h2 class="t w">Evidence that survives a supervisor.</h2>'
             '<p class="lede">Continuous records, functional separation and reconstructable history are what let a regulated '
             'entity adopt a verification layer without inheriting a new counterparty risk.</p>'
             '<div class="mt2"><a class="tl" href="compliance.html">Read the compliance position <span class="ar">&rarr;</span></a></div></div>')
    b.append('<div class="rv" data-i="1"><div class="jshot"><img src="assets/jurisdiction.webp" '
             'alt="Jurisdictional alignment of the Verysset verification layer" style="display:block;width:100%;height:auto" '
             'loading="lazy" decoding="async"></div></div>')
    b.append('</div></div></section>')

    b.append(cta("Start a formal institutional evaluation.",
                 "Evaluation runs on real assets, under your control standards, with structured reporting under NDA."))

    return page("institutions.html",
                "Institutions | Verysset",
                "Institutional validation criteria and twelve actor profiles with expected savings from continuous verification.",
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
        b.append('<button class="mb" role="tab" id="mkb%d" aria-selected="%s" aria-controls="mk-panel" '
                 'data-n="%s" data-t="%s" data-d="%s" data-stats="%s">'
                 '<span class="mi">%s</span>%s<span class="mbt">%s</span></button>'
                 % (i, "true" if i == 0 else "false", n, t, dsc, market_stats_attr(i),
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

    b.append('<section class="sec alt" id="jurisdiction"><div class="wrap"><div class="g2b">')
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
               "Institutional grade infrastructure, backed by leaders across exchanges, tokenization, capital "
               "and fund administration.")]
    b.append('<section class="sec"><div class="wrap">')
    b.append(partner_grid())
    b.append('<p class="lede rv" style="margin-top:30px">Each partner operates in its own regulated lane. '
             'Verysset supplies the verification layer they anchor to, and never the intermediation.</p>')
    b.append('</div></section>')
    b.append('<section class="sec alt"><div class="wrap"><div class="g3">')
    for i, (kn, t, p2) in enumerate([
        ("Exchanges &amp; venues", "Verified listings", "Venues anchor listed instruments to a live twin instead of a filing."),
        ("Tokenization platforms", "Mint against truth", "Platforms mint against a score, not a declaration, and keep the lineage."),
        ("Capital &amp; administration", "Lower reconciliation", "Administrators cut exception handling by reading one continuous record."),
    ]):
        b.append('<div class="card rv" data-i="%d"><div class="rule"></div>'
                 '<span class="mono" style="font-size:10.5px;letter-spacing:.14em;color:var(--faint);text-transform:uppercase">%s</span>'
                 '<h3 style="margin-top:10px">%s</h3><p>%s</p></div>' % (i, kn, t, p2))
    b.append('</div></div></section>')
    b.append(cta("Become a Verysset partner.",
                 "If you operate a venue, a platform or an administration stack, the verification layer plugs in behind it."))
    return page("partners.html", "Partners | Verysset",
                "Institutional grade infrastructure backed by leaders across exchanges, tokenization, capital and fund administration.",
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
    for k in sorted(sizes):
        print("%-22s %7.1f KB" % (k, sizes[k] / 1024.0))
    total, full, miss = i18n_report()
    print("-" * 46)
    print("i18n keys              : %d" % total)
    print("fully translated (6/6) : %d" % full)
    print("english fallback       : %d  (see i18n_missing.json)" % miss)
