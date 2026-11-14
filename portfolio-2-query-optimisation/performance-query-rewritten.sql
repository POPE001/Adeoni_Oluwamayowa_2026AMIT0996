-- Set-based rewrite of performance-query.sql (returns the same result).
-- The original query joins every enrolment x assessment row to mark one
-- probe at a time. Here, marks for the target sections are aggregated once
-- per (section, student) - an access path served by
-- mark_section_assessment_student_idx - and then matched to enrolments.
-- Completeness rules are unchanged: a result needs one mark for every
-- configured assessment, and the section's weights must total 100.
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
WITH target_sections AS (
    SELECT cs.section_id, cs.section_code
    FROM course AS c
    JOIN course_section AS cs USING (course_id)
    JOIN academic_term AS t USING (term_id)
    WHERE c.course_code = 'SYN-0040'
      AND t.academic_year = '2026/2027'
      AND t.term_name = 'First Semester'
),
section_weights AS (
    SELECT a.section_id,
           count(*) AS assessment_count,
           sum(a.weight_percent) AS weight_total
    FROM assessment AS a
    JOIN target_sections AS ts USING (section_id)
    GROUP BY a.section_id
),
mark_totals AS (
    SELECT m.section_id,
           m.student_id,
           count(*) AS mark_count,
           sum(m.score_percent * a.weight_percent) / 100 AS final_percent
    FROM target_sections AS ts
    JOIN assessment AS a USING (section_id)
    JOIN mark AS m USING (section_id, assessment_no)
    GROUP BY m.section_id, m.student_id
)
SELECT ts.section_code,
       count(*) AS students_with_results,
       round(avg(mt.final_percent), 2) AS average_final_percent
FROM target_sections AS ts
JOIN section_weights AS sw USING (section_id)
JOIN mark_totals AS mt USING (section_id)
JOIN enrolment AS e
  ON e.section_id = mt.section_id
 AND e.student_id = mt.student_id
WHERE e.status IN ('enrolled', 'completed')
  AND mt.mark_count = sw.assessment_count
  AND sw.weight_total = 100.00
GROUP BY ts.section_code
ORDER BY ts.section_code;
