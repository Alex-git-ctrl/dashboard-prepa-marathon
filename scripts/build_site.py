"""Assemble plan.json + metrics.json dans docs/index.html, page autonome."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "docs")


def inline(name):
    with open(os.path.join(D, name), encoding="utf-8") as fh:
        return json.dumps(json.load(fh), ensure_ascii=False, separators=(",", ":"))


with open(os.path.join(D, "_template.html"), encoding="utf-8") as fh:
    html = fh.read()

for token, src in (("__PLAN__", "plan.json"), ("__METRICS__", "metrics.json")):
    if token not in html:
        raise SystemExit(f"Placeholder {token} absent du gabarit.")
    html = html.replace(token, inline(src))

out = os.path.join(D, "index.html")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"docs/index.html ecrit : {len(html):,} octets")
