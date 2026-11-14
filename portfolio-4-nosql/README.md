# Portfolio 4: NoSQL and Advanced Data Models

Create a NoSQL representation of data from the same [university portal](../CASE_STUDY.md).

This activity uses a MongoDB document read model for student transcripts. Assessment marks and course results are embedded with the student so a transcript can be read as one document.

## Working files

- [Document model and trade-offs](model.md)
- [PostgreSQL → document export](export-transcripts.sql) and the [exported seed documents](transcripts-seed.ndjson)
- [Load script with schema validator and index](load-data.js)
- [MongoDB queries](queries.js)
- [Run results](run-results.md)
- Seed run: [load output](load-output.txt), [query output](query-results.txt)
- 10,004-student run: [load output](load-output-synthetic.txt), [query output](query-results-synthetic.txt)
- [PostgreSQL cross-check](crosscheck-postgres.sql) and its [output](crosscheck-postgres-output.txt)

## Evidence

- Embedded student transcript document model and trade-off explanation
- Documents generated from the PostgreSQL source, so the read model matches the relational data (including pending and withdrawn results)
- `$jsonSchema` validation with a rejected invalid insert
- Transcript lookup, course results, registrar follow-up, and a cross-check that reproduces the Portfolio 2 PostgreSQL averages
- `explain("executionStats")` comparing the multikey index (628 docs examined) with a collection scan (10,004)

Export from a PostgreSQL database built from Portfolio 1 (optionally with the Portfolio 2 generator), then run the JavaScript files with `mongosh` against a disposable MongoDB database. The current run results are recorded in [run-results.md](run-results.md).
