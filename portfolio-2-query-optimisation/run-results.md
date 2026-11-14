# Query Optimisation Run Results

This run used a temporary local PostgreSQL container. The plan files contain the full `EXPLAIN (ANALYZE, BUFFERS)` output.

## Dataset size

| Relation | Rows |
| --- | ---: |
| `student` | 10,004 |
| `course` | 82 |
| `course_section` | 162 |
| `enrolment` | 50,004 |
| `assessment` | 322 |
| `mark` | 96,784 |

The run used PostgreSQL 16.14. The generated records are synthetic; the generator creates 10,000 students, 80 courses, 160 sections, and 50,000 enrolments on top of the Portfolio 1 seed rows.

The section-capacity check returned 0 violations; the smallest remaining capacity across all sections was 1 seat (the Portfolio 1 sample section).

The weighted-result queries now include only student-section results with a mark for every configured assessment and an assessment-weight total of 100. The result-readiness check is [validate-results.sql](../portfolio-1-database-design/validate-results.sql); captured output is in [result-validation-output.txt](result-validation-output.txt). It correctly flags the ungraded seed section 902 and its enrolment as not result-ready.

## Weighted course-performance query

Run [performance-query.sql](performance-query.sql) after loading the data and collecting planner statistics. Apply [indexes.sql](indexes.sql), then run the same query again.

The captured plans are [before](explain-before.txt) and [after](explain-after.txt).

| Measurement | Before indexes | After indexes |
| --- | --- | --- |
| Execution time | 5.302 ms | 4.173 ms |
| Shared buffer hits / reads | 11,326 / 0 | 10,197 / 6 |
| Main scan and join choices | enrolment primary-key index scan | partial enrolment index-only scan; 0 heap fetches |

The first comparison used a partial enrolment index; PostgreSQL used it for an index-only scan. The mark index was not selected for this student-level workload, so its value is evaluated separately below.

## Section assessment-summary query

Run [assessment-performance-query.sql](assessment-performance-query.sql) before and after the candidate indexes. This workload filters marks by section and assessment, which is the access path targeted by `mark_section_assessment_student_idx`.

The captured plans are [before](assessment-explain-before.txt) and [after](assessment-explain-after.txt). Query results for the representative workloads are in [query-results.txt](query-results.txt).

| Measurement | Before indexes | After indexes |
| --- | --- | --- |
| Execution time | 3.248 ms | 0.558 ms |
| Shared buffer hits / reads | 2,470 / 0 | 30 / 9 |
| Mark-table access path | primary-key index scan by section | section-assessment index-only scan; 0 heap fetches |

For these single-run comparisons, the section-assessment index reduced execution time by about 83% and buffer accesses from 2,470 to 39. The weighted course-performance query ran about 21% faster in its indexed run. Planner choices and timings depend on data and cache state, so treat the timings as indicative and repeat the comparison before making a general performance claim.

The weighted course-performance query returned 304 students with results in each section; the average final percentages were 74.49 for section A and 74.84 for section B. Representative query output is in [query-results.txt](query-results.txt).

The two tables above are the original single-run captures. The repeated-run medians below replace them as the timing evidence.

## Repeated runs and a 10× dataset

Single timings are noisy: the 10k "before" runs ranged from 5.9 ms to 49.2 ms. [benchmark.sh](benchmark.sh) therefore discards two warm-up runs, executes each query 15 times, and reports min, median, and max execution time. [run-comparison.sh](run-comparison.sh) measures every query with the indexes dropped, then again after `indexes.sql`. Both scales ran in fresh PostgreSQL 16.14 containers loaded with `psql -v students=N -f generate-data.sql`:

| Scale | `student` | `enrolment` | `mark` |
| --- | ---: | ---: | ---: |
| 10k | 10,004 | 50,004 | 96,784 |
| 100k | 100,004 | 500,004 | 967,754 |

Median execution time over 15 runs ([10k output](benchmark-10k.txt), [100k output](benchmark-100k.txt)):

| Query | 10k before | 10k after | 100k before | 100k after |
| --- | ---: | ---: | ---: | ---: |
| Weighted performance, original ([performance-query.sql](performance-query.sql)) | 7.87 ms | 4.67 ms | 51.19 ms | 50.59 ms |
| Weighted performance, set-based rewrite ([performance-query-rewritten.sql](performance-query-rewritten.sql)) | 10.37 ms | **2.26 ms** | 85.07 ms | **24.15 ms** |
| Section assessment summary ([assessment-performance-query.sql](assessment-performance-query.sql)) | 3.57 ms | **0.53 ms** | 27.67 ms | **3.00 ms** |

### Why the original weighted query barely improved

At 100k, the index made no difference to the original weighted query (51.19 → 50.59 ms). The [100k plan](explain-100k-original-after.txt) shows why. The new partial enrolment index does its job: an index-only scan with 0 heap fetches and only 43 buffers. But 101,234 of the 101,448 buffer hits come from one node: `Index Scan using mark_pk on mark` executed **12,100 times** (one per enrolment × assessment row) with `Index Cond: (student_id = e.student_id)` only. Section and assessment are applied afterwards as a join filter, which removed 52,834 rows.

The query shape forces one mark lookup per row, and each lookup can only use the leading `student_id` column of `mark_pk`. The new `mark (section_id, assessment_no, student_id)` index can't help a per-student probe, so the planner never picks it. Indexing the cheap part (enrolment) leaves the expensive part (mark probes) unchanged.

### Rewriting the query so the index can be used

[performance-query-rewritten.sql](performance-query-rewritten.sql) returns the same result: at 100k, both versions return section A 3,025 students / 75.03 and section B 3,025 / 75.03. It applies the same completeness rules, but it aggregates marks once per `(section, student)` for the target sections and only then matches the totals to enrolments.

In the [100k rewritten plan](explain-100k-rewritten-after.txt), mark access becomes `Index Only Scan using mark_section_assessment_student_idx` with `Index Cond: (section_id = ...) AND (assessment_no = ...)`, 0 heap fetches, and **85 buffers** for all 12,100 marks. Total buffer hits fell from 101,448 to about 24,300, and the median halved (50.59 → 24.15 ms). At 10k, the median fell from 7.87 ms (original, no index) to 2.26 ms.

The rewrite is **slower than the original without the index** (85.07 vs 51.19 ms at 100k), because aggregating a section's marks then needs a full pass over `mark`. The index and the rewrite only pay off together.

The remaining cost in the rewrite is 6,050 enrolment lookups in a nested loop. The planner estimated 1 row from the `mark_count = assessment_count` join filter, but 6,050 arrived. I tested the alternative with `SET enable_nestloop = off`: it took about 200 ms, so the nested loop is still the better plan here, despite the misestimate.

### What the evidence supports

- The section assessment-summary index gives a consistent 6.7× (10k) to 9.2× (100k) improvement. Its benefit grows with table size, because it replaces a scan over the section's marks with a narrow index-only range read.
- An index helps only if the query's access pattern can use its leading columns. The 100k plan shows the planner ignoring a relevant index because of the query shape, and the rewrite is what turns the index into a 2× gain.
- Single `EXPLAIN ANALYZE` captures (for example, 90.43 ms in the saved 100k plan) are slower than the medians, because they include instrumentation overhead and run once. Use the plan files for structure and buffer counts, and the benchmark files for timing.
