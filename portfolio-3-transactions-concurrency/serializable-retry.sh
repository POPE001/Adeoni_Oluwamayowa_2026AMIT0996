#!/bin/sh
# Client-side retry loop for serializable-enrolment-attempt.sql.
# A SERIALIZABLE transaction aborted with SQLSTATE 40001 is safe to rerun from
# the start; the retry sees the committed winner and makes a fresh decision.
#
# Usage: serializable-retry.sh <student_id> <section_id> [max_attempts]
# Connection settings come from the usual PG* environment variables.

student_id="$1"
section_id="$2"
max_attempts="${3:-5}"
script_dir="$(dirname "$0")"

attempt=1
while [ "$attempt" -le "$max_attempts" ]; do
    echo "=== student $student_id: attempt $attempt ==="
    output="$(psql -X -v student_id="$student_id" -v section_id="$section_id" \
        -f "$script_dir/serializable-enrolment-attempt.sql" 2>&1)"
    status=$?
    echo "$output"
    if [ "$status" -eq 0 ]; then
        echo "=== student $student_id: committed on attempt $attempt ==="
        exit 0
    fi
    if echo "$output" | grep -q '40001'; then
        echo "=== student $student_id: serialization failure (40001), retrying ==="
        attempt=$((attempt + 1))
        continue
    fi
    echo "=== student $student_id: non-retryable error ==="
    exit "$status"
done

echo "=== student $student_id: gave up after $max_attempts attempts ==="
exit 1
