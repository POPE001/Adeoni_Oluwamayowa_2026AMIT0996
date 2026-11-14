#!/bin/sh
# Run an EXPLAIN (ANALYZE) query file repeatedly and report the median
# execution time. Two warm-up runs are discarded so every measured run uses
# a warm buffer cache.
#
# Usage: benchmark.sh <query-file> [runs]
# Connection settings come from the usual PG* environment variables.

query_file="$1"
runs="${2:-15}"

for warm in 1 2; do
    psql -X -At -f "$query_file" > /dev/null
done

times=""
i=1
while [ "$i" -le "$runs" ]; do
    t="$(psql -X -At -f "$query_file" | sed -n 's/^Execution Time: \([0-9.]*\) ms$/\1/p')"
    times="$times $t"
    i=$((i + 1))
done

echo "$times" | tr ' ' '\n' | sed '/^$/d' | sort -n | awk -v f="$query_file" '
    { v[NR] = $1 }
    END {
        median = (NR % 2) ? v[(NR + 1) / 2] : (v[NR / 2] + v[NR / 2 + 1]) / 2
        printf "%s: runs=%d min=%.3f median=%.3f max=%.3f ms\n", f, NR, v[1], median, v[NR]
    }'
