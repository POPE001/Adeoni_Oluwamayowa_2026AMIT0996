# Portfolio 1: Database Design and Modelling

Design a relational database for the [university portal case study](../CASE_STUDY.md).

The design is implemented in PostgreSQL 16. The business rules it enforces are listed in [requirements.md](requirements.md).

## Design files

- [Requirements and business rules](requirements.md)
- [ER diagram](erd.md)
- [PostgreSQL schema](schema.sql)
- [Sample data](seed-data.sql)
- [Drop-after-marks edge-case check](edge-case-check.sql)
- [Final-result readiness validation](validate-results.sql)
- [PostgreSQL run summary](run-verification.md)
- [Normalisation explanation](normalisation.md)
- Captured [schema output](schema-run-output.txt), [seed output](seed-run-output.txt), [edge-case output](edge-case-output.txt), [validation output](validation-output.txt), and [PostgreSQL version](postgres-version.txt)

## Evidence included

- Entity-relationship diagram, requirements, schema, sample data, and normalization explanation
- Rollback-only output covering retained marks, blocked edits/deletes, and blocked mark reassignment
- Result-readiness output identifying sections with invalid assessment totals and enrolments without complete marks
- PostgreSQL run summary with the observed edge-case outcomes

## Key design decisions

- **Multiple lecturers per section.** Team teaching is common, so `section_lecturer` is a many-to-many junction table instead of a single `lecturer_id` column on `course_section`.
- **Only `enrolled` rows consume a seat.** `dropped` and `completed` rows stay for history, but they don't count toward capacity, so a drop frees a seat without deleting the record.
- **The final mark is derived, not stored.** It is calculated from assessment weights and marks (`SUM(score × weight) / 100`), so correcting a mark can never leave a stale stored total.
- **Composite foreign keys on `mark`.** `mark` references `enrolment (student_id, section_id)` and `assessment (section_id, assessment_no)`, so a mark can't be recorded for an assessment from a different section.
- **A trigger handles the drop-after-marks edge case.** Marks are kept but frozen once an enrolment is dropped. This rule depends on another table's state, which a `CHECK` constraint can't express.
