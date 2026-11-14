// Transcript-model queries. Run after load-data.js:
//   mongosh --quiet queries.js
// Queries 1-3 work with the seed export; 4-5 need the synthetic export
// (they use course SYN-0040 from the Portfolio 2 workload).

const portfolioDb = db.getSiblingDB("mit8103_portfolio4");
const transcripts = portfolioDb.studentTranscripts;

// Reusable pipeline: one row per available course result for a course/term.
function courseResults(courseCode) {
  return [
    { $match: { "terms.courses.courseCode": courseCode } },
    { $unwind: "$terms" },
    {
      $match: {
        "terms.academicYear": "2026/2027",
        "terms.termName": "First Semester"
      }
    },
    { $unwind: "$terms.courses" },
    {
      $match: {
        "terms.courses.courseCode": courseCode,
        "terms.courses.resultStatus": "available"
      }
    }
  ];
}

print("1. Transcript lookup by matriculation number (one document read):");
printjson(transcripts.findOne({ _id: "MIT-2026-001" }));

print("2. Available MIT8103 results, 2026/2027 First Semester:");
printjson(
  transcripts
    .aggregate([
      ...courseResults("MIT8103"),
      {
        $project: {
          _id: 1,
          studentName: { $concat: ["$student.firstName", " ", "$student.lastName"] },
          finalPercent: "$terms.courses.finalPercent"
        }
      },
      { $sort: { _id: 1 } }
    ])
    .toArray()
);

print("3. Course results that are not yet available (registrar follow-up):");
printjson(
  transcripts
    .aggregate([
      { $unwind: "$terms" },
      { $unwind: "$terms.courses" },
      { $match: { "terms.courses.resultStatus": { $ne: "available" } } },
      {
        $group: {
          _id: {
            courseCode: "$terms.courses.courseCode",
            resultStatus: "$terms.courses.resultStatus"
          },
          students: { $sum: 1 }
        }
      },
      { $sort: { "_id.courseCode": 1, "_id.resultStatus": 1 } },
      { $limit: 10 }
    ])
    .toArray()
);

if (transcripts.countDocuments({ "terms.courses.courseCode": "SYN-0040" }) > 0) {
  print("4. SYN-0040 results by section (cross-check against the PostgreSQL query in Portfolio 2):");
  printjson(
    transcripts
      .aggregate([
        ...courseResults("SYN-0040"),
        {
          $group: {
            _id: "$terms.courses.sectionCode",
            studentsWithResults: { $sum: 1 },
            averageFinalPercent: { $avg: "$terms.courses.finalPercent" }
          }
        },
        {
          $project: {
            _id: 0,
            sectionCode: "$_id",
            studentsWithResults: 1,
            averageFinalPercent: { $round: ["$averageFinalPercent", 2] }
          }
        },
        { $sort: { sectionCode: 1 } }
      ])
      .toArray()
  );

  print("5. Index evidence: find students with a SYN-0040 result");
  const filter = { "terms.courses.courseCode": "SYN-0040" };
  const summarise = (label, explained) => {
    const stats = explained.executionStats;
    const plan = explained.queryPlanner.winningPlan;
    const stages = [];
    for (let stage = plan; stage; stage = stage.inputStage) {
      stages.push(stage.indexName ? `${stage.stage}(${stage.indexName})` : stage.stage);
    }
    print(
      `${label}: plan=${stages.join(" <- ")}, nReturned=${stats.nReturned}, ` +
        `totalKeysExamined=${stats.totalKeysExamined}, ` +
        `totalDocsExamined=${stats.totalDocsExamined}, ` +
        `executionTimeMillis=${stats.executionTimeMillis}`
    );
  };
  summarise(
    "With multikey index",
    transcripts.find(filter).explain("executionStats")
  );
  summarise(
    "Forced collection scan",
    transcripts.find(filter).hint({ $natural: 1 }).explain("executionStats")
  );
}
