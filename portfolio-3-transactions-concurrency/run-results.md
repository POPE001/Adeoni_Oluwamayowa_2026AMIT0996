# Transactions and Concurrency Run Results

The demonstrations ran in a fresh, disposable PostgreSQL 16.14 database using the Portfolio 1 schema and seed rows.

## Commit and rollback

Run [transaction-examples.sql](transaction-examples.sql). The commit persisted student 1001's email change. The rollback discarded student 1002's temporary email change; the original email remained. Full output is in [transaction-examples-output.txt](transaction-examples-output.txt).

## Unprotected last-seat race

1. Run [reset-concurrency-case.sql](reset-concurrency-case.sql). Section 901 has capacity 3 and starts with 2 active enrolments.
2. Launch two `psql` sessions concurrently, using student IDs 1003 and 1004 with section ID 901, and run [naive-enrolment-attempt.sql](naive-enrolment-attempt.sql) in each.
3. Run [verify-concurrency.sql](verify-concurrency.sql). Both sessions saw 2 active enrolments and each inserted one row, leaving 4 active enrolments against capacity 3. The result is in [naive-verify.txt](naive-verify.txt); session output is in [naive-session-1003.txt](naive-session-1003.txt) and [naive-session-1004.txt](naive-session-1004.txt).

## Row-locking control

1. Run [reset-concurrency-case.sql](reset-concurrency-case.sql) again.
2. Launch the same two sessions concurrently with [locked-enrolment-attempt.sql](locked-enrolment-attempt.sql).
3. Run [verify-concurrency.sql](verify-concurrency.sql). Student 1003 registered; student 1004's insert affected zero rows. The second session waited about 1.58 seconds to acquire the section lock, then saw the committed enrolment. The final count is 3 active enrolments against capacity 3, with no seat remaining. See [locked-verify.txt](locked-verify.txt) and the [session outputs](locked-session-1003.txt), [session 1004](locked-session-1004.txt).

An independent lock-wait check held the section row for six seconds; the second session waited about 5.2 seconds to acquire it. Its output is in [session A](lock-wait-session-a.txt) and [session B](lock-wait-session-b.txt).

## SERIALIZABLE isolation with client retry

This approach uses an isolation level instead of an explicit lock.

1. Run [reset-concurrency-case.sql](reset-concurrency-case.sql). [serializable-verify-before.txt](serializable-verify-before.txt) shows 2 active enrolments against capacity 3.
2. Launch two clients concurrently with [serializable-retry.sh](serializable-retry.sh) (`serializable-retry.sh 1003 901` and `serializable-retry.sh 1004 901`). Each one runs [serializable-enrolment-attempt.sql](serializable-enrolment-attempt.sql) under `BEGIN ISOLATION LEVEL SERIALIZABLE`. This uses the same conditional insert as the locked version, but without `FOR UPDATE`.
3. Both transactions read `active_count = 2` and both inserts returned `INSERT 0 1`. Student 1003 committed first. Student 1004's `COMMIT` failed with `ERROR: 40001: could not serialize access due to read/write dependencies among transactions` (`Canceled on identification as a pivot, during commit attempt`).
4. The client retried. On attempt 2, student 1004 saw `active_count = 3`, inserted 0 rows, and committed cleanly.
5. [serializable-verify.txt](serializable-verify.txt) shows 3 active enrolments against capacity 3. See the session outputs for [student 1003](serializable-session-1003.txt) and [student 1004](serializable-session-1004.txt).

PostgreSQL's Serializable Snapshot Isolation (SSI) records which rows each transaction read, using SIREAD predicate locks. Each transaction read section 901's enrolments and then inserted into that set, which creates a read/write dependency cycle (write skew). No serial order of the two transactions could produce 4 enrolments, so SSI aborts one of them at commit instead of letting the overbooking through.

### Comparing the two controls

| | `READ COMMITTED` + `SELECT ... FOR UPDATE` | `SERIALIZABLE` (SSI) |
| --- | --- | --- |
| How it prevents overbooking | The second transaction blocks on the section row until the first commits (pessimistic). | Both transactions run without blocking; one is aborted at commit if they conflict (optimistic). |
| Observed outcome | Session 1004 waited about 1.58 s, then inserted 0 rows. | Session 1004 failed with `40001`, retried, then inserted 0 rows. |
| Application responsibility | The developer must remember to lock the right row in every code path. | Every code path must handle `40001` with a retry loop, but no lock target has to be chosen. |
| When it suits | Hot, known contention points such as a popular section on registration day. | Many varied transactions where locking rules would be hard to get right; aborts should be rare. |

For this portal, I recommend the row lock for the enrolment path. Registration day concentrates contention on a few known section rows, and blocking for a few milliseconds is cheaper than repeated aborts and retries. `SERIALIZABLE` is the safer default for less predictable administrative transactions.

## Explanation

The unprotected version stores the seat count in each client's `psql` variable before a delay. Both clients therefore make the insert decision using the same count. The row-lock version locks the `course_section` row with `SELECT ... FOR UPDATE` before checking the count. That serialises seat allocation for the section; after the first transaction commits, the waiting transaction's later count statement sees the new enrolment under PostgreSQL's `READ COMMITTED` isolation level.
