// Load transcript documents exported from PostgreSQL (export-transcripts.sql)
// into MongoDB, with a schema validator and the supporting index.
//
//   TRANSCRIPTS_FILE=/path/to/transcripts.ndjson mongosh --quiet load-data.js
//
// The file is newline-delimited JSON, one transcript per student. Use
// transcripts-seed.ndjson (the 4 Portfolio 1 students, committed) or a full
// export from the Portfolio 2 synthetic database (10,004 students).

const fs = require("fs");

const sourceFile = process.env.TRANSCRIPTS_FILE || "transcripts-seed.ndjson";
const portfolioDb = db.getSiblingDB("mit8103_portfolio4");

portfolioDb.studentTranscripts.drop();

// The document model is flexible, but the fields the portal relies on are
// still validated on write.
portfolioDb.createCollection("studentTranscripts", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "studentId", "student", "programme", "terms"],
      properties: {
        _id: { bsonType: "string", description: "matriculation number" },
        studentId: { bsonType: ["int", "long"] },
        terms: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["academicYear", "termName", "courses"],
            properties: {
              courses: {
                bsonType: "array",
                items: {
                  bsonType: "object",
                  required: ["courseCode", "enrolmentStatus", "resultStatus"],
                  properties: {
                    enrolmentStatus: { enum: ["enrolled", "dropped", "completed"] },
                    resultStatus: { enum: ["available", "pending", "withdrawn"] },
                    finalPercent: {
                      bsonType: ["double", "int", "null"],
                      minimum: 0,
                      maximum: 100
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  validationAction: "error"
});

const transcripts = portfolioDb.studentTranscripts;

const lines = fs
  .readFileSync(sourceFile, "utf8")
  .split("\n")
  .filter((line) => line.trim() !== "");

const batchSize = 1000;
let inserted = 0;
for (let i = 0; i < lines.length; i += batchSize) {
  const batch = lines.slice(i, i + batchSize).map((line) => EJSON.parse(line, { relaxed: false }));
  inserted += Object.keys(transcripts.insertMany(batch).insertedIds).length;
}

// Supports "which students have a result for course X?" queries.
transcripts.createIndex({ "terms.courses.courseCode": 1 });

print(`Source file: ${sourceFile}`);
print(`Inserted transcript documents: ${inserted}`);
print(`Collection count: ${transcripts.countDocuments()}`);
print("Indexes:");
printjson(transcripts.getIndexes().map((index) => index.name));

print("Validator check - inserting an invalid resultStatus should fail:");
try {
  transcripts.insertOne({
    _id: "INVALID-TEST",
    studentId: 1,
    student: {},
    programme: {},
    terms: [
      {
        academicYear: "2026/2027",
        termName: "First Semester",
        courses: [
          { courseCode: "X", enrolmentStatus: "enrolled", resultStatus: "passed" }
        ]
      }
    ]
  });
  print("UNEXPECTED: invalid document was accepted");
} catch (error) {
  print(`Rejected as expected: ${error.codeName || error.name} - ${error.errmsg || error.message}`);
}
