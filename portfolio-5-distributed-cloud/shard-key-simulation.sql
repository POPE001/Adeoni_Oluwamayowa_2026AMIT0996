-- Shard-key simulation on a single PostgreSQL node.
-- Hash partitions stand in for shards: PostgreSQL routes rows by hash of the
-- partition key exactly as a sharded system (e.g. Citus) routes by shard key,
-- and partition pruning shows which "shards" each query must touch.
-- Run in a disposable database loaded with Portfolio 1 + the Portfolio 2
-- generator. Runs in a transaction and rolls back.
\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE enrolment_sharded (
    student_id BIGINT NOT NULL,
    section_id BIGINT NOT NULL,
    status VARCHAR(12) NOT NULL,
    enrolled_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (student_id, section_id)
) PARTITION BY HASH (student_id);

CREATE TABLE enrolment_shard_0 PARTITION OF enrolment_sharded FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE enrolment_shard_1 PARTITION OF enrolment_sharded FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE enrolment_shard_2 PARTITION OF enrolment_sharded FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE enrolment_shard_3 PARTITION OF enrolment_sharded FOR VALUES WITH (MODULUS 4, REMAINDER 3);

INSERT INTO enrolment_sharded
SELECT student_id, section_id, status, enrolled_at FROM enrolment;

ANALYZE enrolment_sharded;

\echo '1. Row distribution across the four shards (hash of student_id):'
SELECT tableoid::regclass AS shard, count(*) AS enrolments
FROM enrolment_sharded
GROUP BY tableoid
ORDER BY shard;

\echo '2. Student transcript query (filters on the shard key) - expect ONE shard:'
EXPLAIN (COSTS OFF)
SELECT section_id, status
FROM enrolment_sharded
WHERE student_id = 1001;

\echo '3. Section roster / capacity count (no shard key) - expect ALL shards (scatter-gather):'
EXPLAIN (COSTS OFF)
SELECT count(*)
FROM enrolment_sharded
WHERE section_id = 901
  AND status = 'enrolled';

ROLLBACK;
