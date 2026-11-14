-- Cross-check for queries.js query 4: the same SYN-0040 averages computed in
-- PostgreSQL, both from unrounded finals (as Portfolio 2 reports) and from
-- finals rounded to 2 dp (as stored in the transcript documents).
WITH r AS (
    SELECT cs.section_code,
           e.student_id,
           sum(m.score_percent * a.weight_percent) / 100 AS final_percent
    FROM course AS c
    JOIN course_section AS cs USING (course_id)
    JOIN enrolment AS e USING (section_id)
    JOIN assessment AS a USING (section_id)
    JOIN mark AS m USING (student_id, section_id, assessment_no)
    WHERE c.course_code = 'SYN-0040'
      AND e.status IN ('enrolled', 'completed')
    GROUP BY cs.section_code, e.student_id
    HAVING count(*) = 2
)
SELECT section_code,
       count(*) AS students_with_results,
       round(avg(final_percent), 2) AS avg_unrounded_finals,
       round(avg(round(final_percent, 2)), 2) AS avg_rounded_finals
FROM r
GROUP BY section_code
ORDER BY section_code;
