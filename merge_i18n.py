# -*- coding: utf-8 -*-
"""Merge the per-chunk translator output into i18n_cat.py CAT."""
import glob, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANGS = ["es", "pt", "zh", "ru", "ar"]
DASH = re.compile(u"[—–‒―]")

merged, problems = {}, []
for fp in sorted(glob.glob(os.path.join(HERE, "i18n_work", "out_*.json"))):
    try:
        data = json.load(io.open(fp, encoding="utf-8"))
    except Exception as e:
        problems.append("%s unreadable: %s" % (os.path.basename(fp), e)); continue
    for k, row in data.items():
        clean = {}
        for l in LANGS:
            v = (row.get(l) or "").strip()
            if not v:
                continue
            if DASH.search(v):
                v = DASH.sub(",", v)          # never ship a dash, in any language
            clean[l] = v
        if len(clean) == len(LANGS):
            merged[k] = clean
        else:
            problems.append("%s: incomplete (%s)" % (k, ",".join(sorted(set(LANGS) - set(clean)))))
            if clean:
                merged[k] = clean             # partial rows still beat nothing; missing -> English

# keep the EXTRA block from the existing catalog, rewrite CAT
src = io.open(os.path.join(HERE, "i18n_cat.py"), encoding="utf-8").read()
head = src.split("CAT = {")[0].rstrip() + "\n\nCAT = {\n"

def lit(s):
    return json.dumps(s, ensure_ascii=False)

body = []
for k in sorted(merged):
    row = merged[k]
    body.append("    %s: {%s}," % (lit(k), ", ".join(
        '%s: %s' % (lit(l), lit(row[l])) for l in LANGS if l in row)))
out = head + "\n".join(body) + "\n}\n"
io.open(os.path.join(HERE, "i18n_cat.py"), "w", encoding="utf-8").write(out)

print("merged keys : %d" % len(merged))
print("problems    : %d" % len(problems))
for p in problems[:25]:
    print("  -", p)
