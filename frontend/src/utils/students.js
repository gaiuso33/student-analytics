import { isValidScore } from "./grades";

const round = (n, dp = 1) => Math.round(n * 10 ** dp) / 10 ** dp;

/**
 * Filter records. Keys: search (name or course), course, semester, min, max (score range),
 * risk ("1" keeps only records of at-risk students). Empty values are ignored.
 */
export function filterStudents(students, { search = "", course = "", semester = "", min = "", max = "", risk = "" } = {}) {
  const q = search.trim().toLowerCase();
  const minScore = min === "" ? null : Number(min);
  const maxScore = max === "" ? null : Number(max);

  return students.filter((s) => {
    if (q && !(s.name?.toLowerCase().includes(q) || s.course?.toLowerCase().includes(q))) return false;
    if (course && s.course !== course) return false;
    if (semester && s.semester !== semester) return false;
    if (risk === "1" && s.at_risk !== true) return false;
    // A score bound excludes records with no score (null would otherwise coerce to 0 and pass a max filter)
    const hasBound = (minScore !== null && !Number.isNaN(minScore)) || (maxScore !== null && !Number.isNaN(maxScore));
    if (hasBound && !isValidScore(s.score)) return false;
    if (minScore !== null && !Number.isNaN(minScore) && s.score < minScore) return false;
    if (maxScore !== null && !Number.isNaN(maxScore) && s.score > maxScore) return false;
    return true;
  });
}

/** Sorted unique non-empty values of a field, e.g. distinctValues(rows, "course"). */
export function distinctValues(students, key) {
  return [...new Set(students.map((s) => s[key]).filter((v) => v !== null && v !== undefined && v !== ""))]
    .sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true }));
}

/** Page is clamped into range; returns the slice plus paging info. */
export function paginate(items, page, size) {
  const total = items.length;
  const pageCount = Math.max(1, Math.ceil(total / size));
  const current = Math.min(Math.max(1, page), pageCount);
  const start = (current - 1) * size;
  return { items: items.slice(start, start + size), page: current, pageCount, total, start };
}

/** Numbers sort numerically, strings with localeCompare, nulls always last. */
export function sortStudents(students, { key, direction }) {
  if (!key) return students;
  const dir = direction === "asc" ? 1 : -1;
  return [...students].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    const aNull = av === null || av === undefined || av === "";
    const bNull = bv === null || bv === undefined || bv === "";
    if (aNull && bNull) return 0;
    if (aNull) return 1;
    if (bNull) return -1;
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
    return String(av).localeCompare(String(bv), undefined, { numeric: true, sensitivity: "base" }) * dir;
  });
}

function averageGroups(students, groupKey, valueKey) {
  const map = new Map();
  students.forEach((s) => {
    const group = s[groupKey];
    const value = s[valueKey];
    if (group === null || group === undefined || !isValidScore(value)) return;
    const entry = map.get(group) ?? { total: 0, count: 0 };
    entry.total += value;
    entry.count += 1;
    map.set(group, entry);
  });
  return [...map.entries()].map(([group, { total, count }]) => ({
    group,
    average: total / count,
    count,
  }));
}

/** Average GPA per semester, oldest first (assumes semester labels sort naturally, e.g. "2024-1"). */
export function gpaBySemester(students) {
  return averageGroups(students, "semester", "gpa")
    .sort((a, b) => String(a.group).localeCompare(String(b.group), undefined, { numeric: true }))
    .map(({ group, average }) => ({ semester: String(group), gpa: round(average, 2) }));
}

/** Average score per course, hardest (lowest) first. */
export function courseAverages(students) {
  return averageGroups(students, "course", "score")
    .map(({ group, average, count }) => ({ course: group, avgScore: round(average, 1), students: count }))
    .sort((a, b) => a.avgScore - b.avgScore);
}

export const formatNumber = (value, dp = 2) =>
  typeof value === "number" && Number.isFinite(value) ? value.toFixed(dp) : "--";
