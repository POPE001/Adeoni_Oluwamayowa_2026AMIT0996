# MongoDB Document Model: Student Transcript

## Read pattern

The primary read pattern is “show this student's transcript for a selected academic period.” The document uses the matriculation number as `_id` and embeds the student's programme, terms, course results, and assessment breakdowns. That lets the portal retrieve a transcript with one document read.

## How documents are produced

The documents aren't typed by hand. [export-transcripts.sql](export-transcripts.sql) builds one document per student directly from the normalized PostgreSQL tables (`json_build_object` / `json_agg`), and [load-data.js](load-data.js) loads the resulting newline-delimited JSON into MongoDB. The transcript therefore always agrees with the relational source, and the same business rules carry over:

- `finalPercent` is `SUM(score × weight) / 100`, rounded to 2 dp. It is filled in only when every configured assessment has a mark and the section's weights total 100 (`resultStatus: "available"`). Otherwise it is `null` with `"pending"`.
- A dropped enrolment stays on the transcript with any retained marks, but never gets a final result (`"withdrawn"`). This mirrors the Portfolio 1 trigger rule.
- `enrolmentStatus` is copied unchanged from `enrolment.status`.

## Example document (exported from the Portfolio 1 seed data)

```javascript
{
  _id: "MIT-2026-001",
  studentId: 1001,
  student: { firstName: "Ada", lastName: "Okafor", email: "ada.okafor@example.edu" },
  programme: { code: "MIT", name: "Master of Information Technology" },
  terms: [
    {
      academicYear: "2026/2027",
      termName: "First Semester",
      courses: [
        {
          courseCode: "CSC8101",
          courseTitle: "Database Design",
          creditUnits: 3,
          sectionCode: "A",
          enrolmentStatus: "enrolled",
          assessments: [],            // section 902 has no assessments configured yet
          finalPercent: null,
          resultStatus: "pending"
        },
        {
          courseCode: "MIT8103",
          courseTitle: "Advanced Database Systems",
          creditUnits: 3,
          sectionCode: "A",
          enrolmentStatus: "enrolled",
          assessments: [
            { no: 1, title: "Coursework", weightPercent: 40, scorePercent: 78 },
            { no: 2, title: "Final Examination", weightPercent: 60, scorePercent: 82 }
          ],
          finalPercent: 80.4,
          resultStatus: "available"
        }
      ]
    }
  ]
}
```

All four seed documents are in [transcripts-seed.ndjson](transcripts-seed.ndjson). Zainab Musa's dropped MIT8103 enrolment appears as `"withdrawn"`. Chidi Eze has no enrolments, so his document has `terms: []`.

## Embedding decisions and trade-offs

- Assessment scores are embedded within their course result because they are normally displayed with that result.
- Course code and title are copied into the transcript as a historical snapshot. If the catalogue title changes, an already-issued transcript remains understandable without a cross-collection join.
- The relational PostgreSQL schema remains the normalized source for enrolments, courses, and marks. This document is a read model for transcript retrieval. In this portfolio it is rebuilt by re-running the export. In production, a change-data-capture feed (for example, from PostgreSQL logical decoding, as used in Portfolio 5) would re-export only the affected student's document when a mark or enrolment changes.
- Embedding makes student-centric transcript reads simple, but course-wide reports must scan or unwind documents. The relational model is still a better fit for cross-student registration and aggregate queries.
- The `terms` and `courses` arrays are bounded by a student's study history. If transcript documents approached MongoDB's 16 MB document limit, course results should move to a separate collection keyed by matriculation number and term.

## Schema validation

A document store doesn't remove the need for integrity. `load-data.js` creates the collection with a `$jsonSchema` validator: required top-level fields, `enrolmentStatus` and `resultStatus` limited to their allowed values, and `finalPercent` between 0 and 100 or `null`. The load script then tries to insert a document with `resultStatus: "passed"`, and MongoDB rejects it with `Document failed validation`.

## Indexing

MongoDB's built-in unique `_id` index supports transcript lookups by matriculation number. A multikey index on `terms.courses.courseCode` supports queries that find students with a result for a given course.

With the 10,004-student export, `find({"terms.courses.courseCode": "SYN-0040"})` used `IXSCAN(terms.courses.courseCode_1)` and examined 628 keys and 628 documents to return 628. With a forced collection scan, it examined all 10,004 documents (9 ms vs 0 ms).
