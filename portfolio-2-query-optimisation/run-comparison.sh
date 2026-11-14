#!/bin/sh
# Median timings for the original queries and the set-based rewrite, before
# and after indexes.sql, in a database already loaded by generate-data.sql.
# Usage: run-comparison.sh [runs]
set -e
runs="${1:-15}"
dir="$(dirname "$0")"
queries="performance-query.sql performance-query-rewritten.sql assessment-performance-query.sql"

psql -X -q -c "DROP INDEX IF EXISTS enrolment_section_result_student_idx" \
            -c "DROP INDEX IF EXISTS mark_section_assessment_student_idx" \
            -c "ANALYZE enrolment" -c "ANALYZE mark"
echo "--- before indexes"
for q in $queries; do "$dir/benchmark.sh" "$dir/$q" "$runs"; done
psql -X -q -v ON_ERROR_STOP=1 -f "$dir/indexes.sql"
echo "--- after indexes"
for q in $queries; do "$dir/benchmark.sh" "$dir/$q" "$runs"; done
