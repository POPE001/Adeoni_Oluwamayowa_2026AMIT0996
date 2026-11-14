# Screenshot evidence

Each image shows captured terminal output from the disposable PostgreSQL 16.14 and MongoDB 7.0.45 runs. The title bar of every panel names the committed output file it shows, so each screenshot can be checked against the raw evidence. Panels marked `[excerpt: matching lines only]` show selected plan lines. In the Portfolio 2 plan excerpts, planner cost estimates are also removed so the lines fit; the full plans are in the linked files. The ER diagram is rendered from the Mermaid source in [erd.md](../../portfolio-1-database-design/erd.md).

Regenerate with `python3 final-documentation/screenshots/render-screenshots.py` from the repository root (requires Google Chrome).

| Image | Shows |
| --- | --- |
| [01-er-diagram.png](01-er-diagram.png) | Portfolio 1 ER diagram |
| [02-p1-edge-case-and-validation.png](02-p1-edge-case-and-validation.png) | Mark-protection trigger checks (4 × PASS) and result-readiness validation |
| [03-p2-plans-100k.png](03-p2-plans-100k.png) | 100k-student plans: 12,100 `mark_pk` probes vs the rewrite's index-only scan |
| [04-p2-median-benchmarks.png](04-p2-median-benchmarks.png) | 15-run medians before/after indexes at 10k and 100k |
| [05-p3-naive-overbooking.png](05-p3-naive-overbooking.png) | Unprotected race: 4 enrolments for 3 seats |
| [06-p3-row-lock.png](06-p3-row-lock.png) | `FOR UPDATE`: second session waits ~1.58 s, inserts 0 rows |
| [07-p3-serializable-retry.png](07-p3-serializable-retry.png) | `SERIALIZABLE`: `40001` on commit, retry inserts 0 rows |
| [08-p4-mongodb.png](08-p4-mongodb.png) | Validator rejection, PostgreSQL cross-check, `IXSCAN` vs `COLLSCAN` |
| [09-p5-replication-stale-read.png](09-p5-replication-stale-read.png) | Streaming status, stale replica read while paused, catch-up |
| [10-p5-shard-key.png](10-p5-shard-key.png) | Shard distribution; 1-shard vs 4-shard query plans |
