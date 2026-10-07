export const GRADES = ["A", "B", "C", "D", "F"];
export const PASS_MARK = 60; // keep in sync with the backend pass-rate rule

export function isValidScore(score) {
  return typeof score === "number" && Number.isFinite(score);
}

export function gradeFor(score) {
  if (score >= 90) return "A";
  if (score >= 80) return "B";
  if (score >= 70) return "C";
  if (score >= 60) return "D";
  return "F";
}

export function gradeDistribution(students) {
  const counts = Object.fromEntries(GRADES.map((g) => [g, 0]));
  students.forEach((s) => {
    if (isValidScore(s.score)) counts[gradeFor(s.score)] += 1;
  });
  return GRADES.map((grade) => ({ grade, students: counts[grade] }));
}
