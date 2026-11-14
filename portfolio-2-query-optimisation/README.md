# Portfolio 2: Query Processing and Optimisation

Apply query processing and optimisation to the [university portal](../CASE_STUDY.md), using the relational schema from Portfolio 1.

The workload uses a reproducible synthetic dataset and compares the same course-performance query before and after adding indexes.

## Working files

- [Synthetic data generator](generate-data.sql)
- [Representative queries](queries.sql)
- [Performance query](performance-query.sql) and its [set-based rewrite](performance-query-rewritten.sql)
- [Section assessment summary query](assessment-performance-query.sql)
- [Indexes under evaluation](indexes.sql)
- [Final-result completeness and weight validation](../portfolio-1-database-design/validate-results.sql)
- [Benchmark script](benchmark.sh) (15-run median) and [before/after comparison](run-comparison.sh)
- [Run results](run-results.md)
- Median timings at [10k](benchmark-10k.txt) and [100k](benchmark-100k.txt) students; 100k plans for the [original](explain-100k-original-after.txt) and [rewritten](explain-100k-rewritten-after.txt) query
- [Validation output](result-validation-output.txt)
- [Representative query output](query-results.txt)
- [Weighted query plans before and after indexes](explain-before.txt), [after](explain-after.txt)
- [Section assessment plans before and after indexes](assessment-explain-before.txt), [after](assessment-explain-after.txt)

## Evidence included

- Representative SQL queries and captured query results
- Before-and-after `EXPLAIN (ANALYZE, BUFFERS)` plans for both workloads
- Candidate indexes and a brief analysis of plan changes, timings, buffer activity, and dataset size
- 15-run median timings at two scales (10k and 100k students), showing why indexing alone didn't help the weighted query at 100k and how a query rewrite made the new index usable
- Weighted-result queries that exclude incomplete mark sets and sections whose assessment weights do not total 100

Run Portfolio 1's `schema.sql` and `seed-data.sql` in a fresh database first, then run `generate-data.sql`. Capture both performance queries before applying `indexes.sql` and again afterward. For the median comparison, load with `psql -v students=100000 -f generate-data.sql` (or the default 10,000) and run `run-comparison.sh`.
