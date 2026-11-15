#!/usr/bin/env python3
"""Build portfolio-summary.pdf from portfolio-summary.md with headless Chrome.

Usage (from anywhere): python3 final-documentation/build-pdf.py
The summary text is set at 10pt on A4; the screenshot appendix starts on a
new page. Requires Google Chrome and network access to cdn.jsdelivr.net
(marked.js, used to render the Markdown).
"""

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SOURCE = HERE / "portfolio-summary.md"
TARGET = HERE / "portfolio-summary.pdf"

markdown = SOURCE.read_text()
if "[TO COMPLETE" in markdown:
    print("WARNING: the summary still contains a [TO COMPLETE ...] placeholder.", file=sys.stderr)

page = f"""<!doctype html><html><head><meta charset="utf-8">
<style>
@page {{ size: A4; margin: 16mm 17mm; }}
body {{ font: 10pt/1.38 Georgia, 'Times New Roman', serif; color: #111; }}
h1 {{ font: bold 15pt Helvetica, Arial, sans-serif; margin: 0 0 6pt; }}
h2 {{ font: bold 11pt Helvetica, Arial, sans-serif; margin: 10pt 0 3pt; border-bottom: 0.5pt solid #999; padding-bottom: 1pt; }}
p, li {{ margin: 0 0 5pt; text-align: justify; }}
ul {{ margin: 0 0 5pt; padding-left: 16pt; }}
code {{ font: 8.6pt Menlo, Consolas, monospace; background: #f1f1f1; padding: 0 2pt; border-radius: 2pt; }}
a {{ color: #0b4f9c; text-decoration: none; }}
h2#appendix {{ break-before: page; }}
img {{ display: block; max-width: 100%; max-height: 118mm; margin: 4pt auto 8pt; border: 0.5pt solid #ccc; break-inside: avoid; }}
</style></head><body><div id="content"></div>
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<script>
const md = {json.dumps(markdown)};
document.getElementById("content").innerHTML = marked.parse(md);
// Relative links point at repository files: send them to GitHub, not file://.
const repoBase = "https://github.com/POPE001/Adeoni_Oluwamayowa_2026AMIT0996/blob/main/final-documentation/";
for (const a of document.querySelectorAll("a[href]")) {{
  const href = a.getAttribute("href");
  if (!/^[a-z]+:/i.test(href) && !href.startsWith("#")) a.href = new URL(href, repoBase).href;
}}
for (const h of document.querySelectorAll("h2")) {{
  if (h.textContent.startsWith("Appendix")) h.id = "appendix";
}}
</script></body></html>"""

tmp = HERE / ".summary-print.html"
tmp.write_text(page)
try:
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         "--virtual-time-budget=15000", f"--print-to-pdf={TARGET}", f"file://{tmp}"],
        check=True, capture_output=True,
    )
finally:
    tmp.unlink(missing_ok=True)
print(f"wrote {TARGET}")
