# NoSQL Run Results

## Environment

MongoDB 7.0.45 in a disposable container; database `mit8103_portfolio4`; collection `studentTranscripts`. The source data came from PostgreSQL 16.14 containers built with the Portfolio 1 schema and seed data, plus the Portfolio 2 synthetic workload for the large run.

## Run sequence

1. Export from PostgreSQL: `psql -X -At -f export-transcripts.sql > transcripts.ndjson`.
2. Load: `TRANSCRIPTS_FILE=transcripts.ndjson mongosh --quiet load-data.js`.
3. Query: `mongosh --quiet queries.js`.

This was run twice:

| Run | Source | Documents | Load output | Query output |
| --- | --- | ---: | --- | --- |
| Seed | Portfolio 1 seed data ([transcripts-seed.ndjson](transcripts-seed.ndjson), committed) | 4 | [load-output.txt](load-output.txt) | [query-results.txt](query-results.txt) |
| Synthetic | Portfolio 2 database with 10,000 generated students (23 MB export, regenerated rather than committed) | 10,004 | [load-output-synthetic.txt](load-output-synthetic.txt) | [query-results-synthetic.txt](query-results-synthetic.txt) |

## Results

- **Validator.** Both loads rejected a test document with `resultStatus: "passed"` (`MongoServerError - Document failed validation`).
- **Transcript lookup.** `findOne({_id: "MIT-2026-001"})` returned Ada Okafor's full transcript in one document read: MIT8103 `available` at 80.4, and CSC8101 `pending` because section 902 has no assessments. This matches the PostgreSQL validation output from Portfolio 1.
- **Course results.** Available MIT8103 results were Ada Okafor (80.4) and Tunde Bello (70.4). Zainab Musa's dropped enrolment is excluded as `withdrawn`.
- **Registrar follow-up.** Grouping non-available results gave CSC8101 `pending` ×1 and MIT8103 `withdrawn` ×1 for the seed data. The synthetic run also shows the generated drops (for example, SYN-0001 `withdrawn` ×20).
- **Cross-check with PostgreSQL.** For SYN-0040, MongoDB returned 304 results in each section, averaging 74.50 (A) and 74.84 (B). Portfolio 2's PostgreSQL query reports 304 / 74.49 and 304 / 74.84. The 0.01 difference in section A comes from rounding: the transcript stores each student's final rounded to 2 dp, as an issued transcript would. [crosscheck-postgres.sql](crosscheck-postgres.sql) confirms that averaging the rounded finals in PostgreSQL also gives 74.50 ([output](crosscheck-postgres-output.txt)).
- **Index evidence.** For students with a SYN-0040 result, the multikey index plan was `FETCH <- IXSCAN(terms.courses.courseCode_1)`: 628 keys and 628 documents examined, 628 returned, 0 ms. A forced `COLLSCAN` examined all 10,004 documents for the same 628 results (9 ms).

## Notes

The containers were disposable and were removed after the run. PostgreSQL remains the normalized source of truth, and MongoDB holds a derived, read-optimized copy.
