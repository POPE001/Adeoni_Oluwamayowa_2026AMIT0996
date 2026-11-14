#!/usr/bin/env python3
"""Render captured portfolio output files as terminal-window PNG screenshots.

Every panel shows the verbatim contents (or a marked excerpt) of an evidence
file committed in this repository, captured from the disposable PostgreSQL
16.14 / MongoDB 7.0.45 runs. Nothing is typed in by hand; the source file of
each panel is printed in its title bar.

Usage (from the repository root):
    python3 final-documentation/screenshots/render-screenshots.py

Requires Google Chrome (headless) for HTML -> PNG.
"""

import html
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

LINE_PX = 17
CHAR_PX = 7.25


def read(path, start=None, end=None, grep=None, strip_cost=False):
    """Return a file's text, optionally a 1-based inclusive line range or only
    lines matching a regex (an excerpt marker is added when lines are cut)."""
    lines = (ROOT / path).read_text().rstrip("\n").split("\n")
    if start or end:
        cut = lines[(start or 1) - 1 : end]
        prefix = ["[...]"] if (start or 1) > 1 else []
        suffix = ["[...]"] if end and end < len(lines) else []
        lines = prefix + cut + suffix
    if grep:
        lines = [l for l in lines if re.search(grep, l)]
        lines = ["[excerpt: matching lines only]"] + lines
    if strip_cost:
        # Drop planner cost estimates and deep indentation so plan nodes fit.
        lines = [re.sub(r"  \(cost=[^)]*\)", "", l) for l in lines]
        lines = [re.sub(r"^( {2,})", lambda m: " " * min(len(m.group(1)) // 3, 24), l) for l in lines]
    return "\n".join(lines)


def highlight(text):
    out = html.escape(text)
    rules = [
        (r"(ERROR:.*|could not serialize.*)", "err"),
        (r"(NOTICE:\s+PASS.*|Rejected as expected.*|committed on attempt \d+)", "ok"),
        (r"(INSERT 0 [01]|COMMIT|ROLLBACK|BEGIN(?: ISOLATION LEVEL SERIALIZABLE)?)$", "kw"),
        (r"(Execution Time: [0-9.]+ ms|median=[0-9.]+)", "hl"),
        (r"(\[\.\.\.\]|\[excerpt: matching lines only\])", "dim"),
    ]
    for pattern, cls in rules:
        out = re.sub(pattern, rf'<span class="{cls}">\1</span>', out, flags=re.M)
    return out


CSS = """
body { margin: 0; padding: 18px; background: #e9ecef; font-family: -apple-system, Helvetica, sans-serif; }
h1 { font-size: 15px; margin: 0 0 12px; color: #212529; }
.grid { display: grid; gap: 14px; }
.win { background: #1e1e1e; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.25); }
.bar { background: #3a3a3a; color: #ddd; font-size: 11.5px; padding: 6px 10px; display: flex; gap: 8px; align-items: center; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.cmd { color: #9cdcfe; font-family: Menlo, monospace; font-size: 11.5px; padding: 8px 12px 0; white-space: pre-wrap; }
pre { margin: 0; padding: 6px 12px 12px; color: #d4d4d4; font: 12px/17px Menlo, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
.err { color: #f48771; font-weight: bold; }
.ok { color: #89d185; font-weight: bold; }
.kw { color: #c586c0; }
.hl { color: #ffd866; font-weight: bold; }
.dim { color: #808080; font-style: italic; }
"""


def panel(source, command, text):
    return f"""<div class="win"><div class="bar">
<span class="dot" style="background:#ff5f56"></span><span class="dot" style="background:#ffbd2e"></span>
<span class="dot" style="background:#27c93f"></span><span>{html.escape(source)}</span></div>
<div class="cmd">$ {html.escape(command)}</div><pre>{highlight(text)}</pre></div>"""


def render_html(name, html_doc, width, height, budget_ms=0):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html_doc)
        tmp = f.name
    args = [
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2",
        f"--window-size={width},{height}",
        f"--screenshot={OUT / name}",
    ]
    if budget_ms:
        args.append(f"--virtual-time-budget={budget_ms}")
    subprocess.run(args + [f"file://{tmp}"], check=True, capture_output=True)
    print(f"wrote {name}")


def shot(name, title, rows, width=None):
    """rows: list of rows; each row is a list of (source, command, text)."""
    grid_rows = []
    total_h = 60
    max_w = 0
    for row in rows:
        cols = len(row)
        widest = max(max(len(l) for l in t.split("\n")) for _, _, t in row)
        max_w = max(max_w, cols * (widest * CHAR_PX + 40) + (cols - 1) * 14)
    page_w = width or int(max(max_w + 40, 700))
    for row in rows:
        cols = len(row)
        chars_per_line = max(20, int(((page_w - 36 - (cols - 1) * 14) / cols - 24) / CHAR_PX))
        tallest = max(sum(max(1, -(-len(l) // chars_per_line)) for l in t.split("\n")) for _, _, t in row)
        total_h += tallest * LINE_PX + 80
        cells = "".join(panel(*p) for p in row)
        grid_rows.append(
            f'<div class="grid" style="grid-template-columns: repeat({cols}, 1fr); margin-bottom: 14px">{cells}</div>'
        )
    width = page_w
    doc = f"<!doctype html><meta charset='utf-8'><style>{CSS}</style><h1>{html.escape(title)}</h1>{''.join(grid_rows)}"
    render_html(name, doc, width, int(total_h))


def er_diagram():
    md = (ROOT / "portfolio-1-database-design/erd.md").read_text()
    mermaid = re.search(r"```mermaid\n(.*?)```", md, re.S).group(1)
    doc = f"""<!doctype html><meta charset="utf-8">
<style>body {{ margin: 0; padding: 16px; background: #fff; font-family: Helvetica, sans-serif; }}
h1 {{ font-size: 15px; margin: 0 0 8px; }}</style>
<h1>Portfolio 1 - ER diagram (rendered from portfolio-1-database-design/erd.md)</h1>
<pre class="mermaid">{html.escape(mermaid)}</pre>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{ startOnLoad: true, theme: "default", er: {{ useMaxWidth: false }} }});</script>"""
    render_html("01-er-diagram.png", doc, 1500, 1250, budget_ms=15000)


P1 = "portfolio-1-database-design/"
P2 = "portfolio-2-query-optimisation/"
P3 = "portfolio-3-transactions-concurrency/"
P4 = "portfolio-4-nosql/"
P5 = "portfolio-5-distributed-cloud/"


def main():
    er_diagram()

    shot("02-p1-edge-case-and-validation.png",
         "Portfolio 1 - trigger protects marks after a drop; result-readiness validation",
         [[(P1 + "edge-case-output.txt", "psql -f edge-case-check.sql", read(P1 + "edge-case-output.txt"))],
          [(P1 + "validation-output.txt", "psql -f validate-results.sql", read(P1 + "validation-output.txt"))]])

    plan_nodes = r"(Index|Seq) (Only )?Scan|Index Cond|Heap Fetches|Execution Time|^ +Buffers: shared hit=\d{4,}"
    shot("03-p2-plans-100k.png",
         "Portfolio 2 - 100k students: original query probes mark 12,100 times; rewrite uses the new index",
         [[(P2 + "explain-100k-original-after.txt", "psql -f performance-query.sql   # indexes applied",
            read(P2 + "explain-100k-original-after.txt", grep=plan_nodes, strip_cost=True)),
           (P2 + "explain-100k-rewritten-after.txt", "psql -f performance-query-rewritten.sql   # indexes applied",
            read(P2 + "explain-100k-rewritten-after.txt", grep=plan_nodes, strip_cost=True))]],
         width=1700)

    shot("04-p2-median-benchmarks.png",
         "Portfolio 2 - 15-run median execution times, before and after indexes.sql",
         [[(P2 + "benchmark-10k.txt", "run-comparison.sh 15   # 10,004 students", read(P2 + "benchmark-10k.txt")),
           (P2 + "benchmark-100k.txt", "run-comparison.sh 15   # 100,004 students", read(P2 + "benchmark-100k.txt"))]])

    shot("05-p3-naive-overbooking.png",
         "Portfolio 3 - READ COMMITTED without a lock: both sessions take the last seat (4 of 3)",
         [[(P3 + "naive-session-1003.txt", "psql -v student_id=1003 -v section_id=901 -f naive-enrolment-attempt.sql",
            read(P3 + "naive-session-1003.txt")),
           (P3 + "naive-session-1004.txt", "psql -v student_id=1004 -v section_id=901 -f naive-enrolment-attempt.sql",
            read(P3 + "naive-session-1004.txt"))],
          [(P3 + "naive-verify.txt", "psql -f verify-concurrency.sql", read(P3 + "naive-verify.txt"))]])

    shot("06-p3-row-lock.png",
         "Portfolio 3 - SELECT ... FOR UPDATE: session 1004 waits ~1.58 s, then inserts 0 rows (3 of 3)",
         [[(P3 + "locked-session-1003.txt", "psql -v student_id=1003 -v section_id=901 -f locked-enrolment-attempt.sql",
            read(P3 + "locked-session-1003.txt")),
           (P3 + "locked-session-1004.txt", "psql -v student_id=1004 -v section_id=901 -f locked-enrolment-attempt.sql",
            read(P3 + "locked-session-1004.txt"))],
          [(P3 + "locked-verify.txt", "psql -f verify-concurrency.sql", read(P3 + "locked-verify.txt"))]])

    shot("07-p3-serializable-retry.png",
         "Portfolio 3 - SERIALIZABLE: session 1004 aborted with 40001, retried, inserted 0 rows (3 of 3)",
         [[(P3 + "serializable-session-1003.txt", "serializable-retry.sh 1003 901", read(P3 + "serializable-session-1003.txt")),
           (P3 + "serializable-session-1004.txt", "serializable-retry.sh 1004 901", read(P3 + "serializable-session-1004.txt"))],
          [(P3 + "serializable-verify.txt", "psql -f verify-concurrency.sql", read(P3 + "serializable-verify.txt"))]],
         width=1500)

    synthetic = (ROOT / P4 / "query-results-synthetic.txt").read_text().split("\n")
    start = next(i for i, l in enumerate(synthetic) if l.startswith("4.")) + 1
    shot("08-p4-mongodb.png",
         "Portfolio 4 - MongoDB transcripts generated from PostgreSQL: validator, cross-check, index evidence",
         [[(P4 + "load-output-synthetic.txt", "TRANSCRIPTS_FILE=transcripts.ndjson mongosh --quiet load-data.js",
            read(P4 + "load-output-synthetic.txt")),
           (P4 + "crosscheck-postgres-output.txt", "psql -f crosscheck-postgres.sql   # same averages in PostgreSQL",
            read(P4 + "crosscheck-postgres-output.txt"))],
          [(P4 + "query-results-synthetic.txt", "mongosh --quiet queries.js   # queries 4-5",
            read(P4 + "query-results-synthetic.txt", start=start))]],
         width=1700)

    shot("09-p5-replication-stale-read.png",
         "Portfolio 5 - logical replication: stale read while paused, catch-up after resume",
         [[(P5 + "status-primary-output.txt", "primary$ psql -f status-primary.sql", read(P5 + "status-primary-output.txt"))],
          [(P5 + "pause-output.txt", "replica$ psql -f pause-replication.sql", read(P5 + "pause-output.txt")),
           (P5 + "primary-write-output.txt", "primary$ psql -f write-primary.sql", read(P5 + "primary-write-output.txt")),
           (P5 + "replica-stale-output.txt", "replica$ psql -f verify-replica.sql   # STALE", read(P5 + "replica-stale-output.txt"))],
          [(P5 + "resume-output.txt", "replica$ psql -f resume-replication.sql", read(P5 + "resume-output.txt")),
           (P5 + "replica-caught-up-output.txt", "replica$ psql -f verify-replica.sql   # CAUGHT UP",
            read(P5 + "replica-caught-up-output.txt"))]],
         width=1500)

    shot("10-p5-shard-key.png",
         "Portfolio 5 - shard-key simulation: student query hits 1 shard, section capacity count hits all 4",
         [[(P5 + "shard-key-simulation-output.txt", "psql -f shard-key-simulation.sql",
            read(P5 + "shard-key-simulation-output.txt", start=9))]])


if __name__ == "__main__":
    main()
