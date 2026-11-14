-- SERIALIZABLE alternative to the row-lock version.
-- Run in two sessions at the same time with different student_id values.
-- No explicit lock is taken. PostgreSQL's Serializable Snapshot Isolation
-- (SSI) tracks the read of section 901's enrolments; if a concurrent
-- transaction inserts into that same set, one transaction is aborted with
-- SQLSTATE 40001 (serialization_failure) and must be retried by the client.
\set ON_ERROR_STOP on
\set VERBOSITY verbose
\timing on

BEGIN ISOLATION LEVEL SERIALIZABLE;

SHOW transaction_isolation;

-- Read the seat position without locking anything.
SELECT cs.capacity,
       count(e.student_id) FILTER (WHERE e.status = 'enrolled') AS active_count
FROM course_section AS cs
LEFT JOIN enrolment AS e USING (section_id)
WHERE cs.section_id = :section_id
GROUP BY cs.capacity;

-- Widen the race window so both sessions read before either writes.
SELECT pg_sleep(2);

-- Same conditional insert as the locked version, but without FOR UPDATE.
INSERT INTO enrolment (student_id, section_id, status)
SELECT :student_id, :section_id, 'enrolled'
WHERE (SELECT count(*)
       FROM enrolment
       WHERE section_id = :section_id
         AND status = 'enrolled')
    < (SELECT capacity
       FROM course_section
       WHERE section_id = :section_id)
ON CONFLICT (student_id, section_id) DO NOTHING;

COMMIT;
