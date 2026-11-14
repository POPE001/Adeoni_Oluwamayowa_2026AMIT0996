-- Build one MongoDB transcript document per student from the normalized
-- PostgreSQL source (Portfolio 1 schema), as newline-delimited JSON.
--
--   psql -X -At -f export-transcripts.sql > transcripts.ndjson
--
-- Rules carried over from the relational model:
--   * finalPercent = SUM(score * weight) / 100, only when every configured
--     assessment has a mark and the section's weights total 100
--     (resultStatus "available"); otherwise null with "pending".
--   * Dropped enrolments are kept with any retained marks, never a final
--     result (resultStatus "withdrawn").
--   * Course code/title are copied into the document as a snapshot.

WITH assessment_rows AS (
    SELECT e.student_id,
           e.section_id,
           json_agg(
               json_build_object(
                   'no', a.assessment_no,
                   'title', a.title,
                   'weightPercent', a.weight_percent,
                   'scorePercent', m.score_percent
               ) ORDER BY a.assessment_no
           ) AS assessments,
           count(a.assessment_no) AS assessment_count,
           count(m.assessment_no) AS mark_count,
           sum(a.weight_percent) AS weight_total,
           sum(m.score_percent * a.weight_percent) / 100 AS weighted_percent
    FROM enrolment AS e
    JOIN assessment AS a ON a.section_id = e.section_id
    LEFT JOIN mark AS m
      ON m.student_id = e.student_id
     AND m.section_id = e.section_id
     AND m.assessment_no = a.assessment_no
    GROUP BY e.student_id, e.section_id
),
course_rows AS (
    SELECT e.student_id,
           t.term_id,
           t.academic_year,
           t.term_name,
           t.starts_on,
           c.course_code,
           json_build_object(
               'courseCode', c.course_code,
               'courseTitle', c.title,
               'creditUnits', c.credit_units,
               'sectionCode', cs.section_code,
               'enrolmentStatus', e.status,
               'assessments', coalesce(ar.assessments, '[]'::json),
               'finalPercent',
                   CASE
                       WHEN e.status <> 'dropped'
                        AND ar.assessment_count > 0
                        AND ar.mark_count = ar.assessment_count
                        AND ar.weight_total = 100
                       THEN round(ar.weighted_percent, 2)
                   END,
               'resultStatus',
                   CASE
                       WHEN e.status = 'dropped' THEN 'withdrawn'
                       WHEN ar.assessment_count > 0
                        AND ar.mark_count = ar.assessment_count
                        AND ar.weight_total = 100 THEN 'available'
                       ELSE 'pending'
                   END
           ) AS course_doc
    FROM enrolment AS e
    JOIN course_section AS cs USING (section_id)
    JOIN course AS c USING (course_id)
    JOIN academic_term AS t USING (term_id)
    LEFT JOIN assessment_rows AS ar
      ON ar.student_id = e.student_id
     AND ar.section_id = e.section_id
),
term_rows AS (
    SELECT student_id,
           starts_on,
           json_build_object(
               'academicYear', academic_year,
               'termName', term_name,
               'courses', json_agg(course_doc ORDER BY course_code)
           ) AS term_doc
    FROM course_rows
    GROUP BY student_id, term_id, academic_year, term_name, starts_on
)
SELECT json_build_object(
           '_id', s.matric_number,
           'studentId', s.student_id,
           'student', json_build_object(
               'firstName', s.first_name,
               'lastName', s.last_name,
               'email', s.email
           ),
           'programme', json_build_object('code', p.code, 'name', p.name),
           'terms', coalesce(
               (SELECT json_agg(tr.term_doc ORDER BY tr.starts_on)
                FROM term_rows AS tr
                WHERE tr.student_id = s.student_id),
               '[]'::json
           )
       )
FROM student AS s
JOIN programme AS p USING (programme_id)
ORDER BY s.student_id;
