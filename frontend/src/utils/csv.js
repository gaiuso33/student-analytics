import { gradeFor, isValidScore } from "./grades";

/** Quote a CSV cell. Text starting with = + - @ is prefixed so Excel can't run it as a formula. */
export function escapeCell(value) {
  if (value === null || value === undefined) return "";
  let text = String(value);
  if (typeof value === "string" && /^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  if (/[",\r\n]/.test(text)) text = `"${text.replace(/"/g, '""')}"`;
  return text;
}

/** columns: [{ header, value: (row) => cell }] */
export function toCsv(rows, columns) {
  const header = columns.map((c) => escapeCell(c.header)).join(",");
  const lines = rows.map((row) => columns.map((c) => escapeCell(c.value(row))).join(","));
  return [header, ...lines].join("\r\n");
}

const STUDENT_COLUMNS = [
  { header: "Student", value: (r) => r.name },
  { header: "Course", value: (r) => r.course },
  { header: "Semester", value: (r) => r.semester },
  { header: "Score", value: (r) => r.score },
  { header: "Grade", value: (r) => (isValidScore(r.score) ? gradeFor(r.score) : "") },
  { header: "GPA", value: (r) => r.gpa },
  { header: "At risk", value: (r) => (r.at_risk ? "Yes" : "No") },
];

export function studentsToCsv(rows) {
  return toCsv(rows, STUDENT_COLUMNS);
}

/** Trigger a browser download. A BOM is added so Excel reads UTF-8 names correctly. */
export function downloadCsv(filename, csv) {
  const blob = new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
