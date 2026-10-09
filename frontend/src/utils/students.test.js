import { describe, it, expect } from "vitest";
import {
  filterStudents, sortStudents, paginate, distinctValues, gpaBySemester, courseAverages,
} from "./students";

const rows = [
  { id: 1, name: "Ada Eze", course: "Math", semester: "2024-1", score: 55, gpa: 0, at_risk: true },
  { id: 2, name: "bola Lawal", course: "Physics", semester: "2024-2", score: 91, gpa: 4, at_risk: false },
  { id: 3, name: "Chi Okafor", course: "Math", semester: "2024-2", score: null, gpa: 2, at_risk: false },
];

describe("filterStudents", () => {
  it("returns everything when no filters are set", () => {
    expect(filterStudents(rows, {})).toHaveLength(3);
  });
  it("searches name and course case-insensitively", () => {
    expect(filterStudents(rows, { search: "ADA" })).toHaveLength(1);
    expect(filterStudents(rows, { search: "phys" })).toHaveLength(1);
  });
  it("filters by course and semester", () => {
    expect(filterStudents(rows, { course: "Math" })).toHaveLength(2);
    expect(filterStudents(rows, { semester: "2024-2" })).toHaveLength(2);
  });
  it("filters by score range and drops records with no score when a bound is set", () => {
    expect(filterStudents(rows, { min: "60" }).map((r) => r.id)).toEqual([2]);
    expect(filterStudents(rows, { max: "60" }).map((r) => r.id)).toEqual([1]);
  });
  it("keeps only at-risk students when risk is set", () => {
    expect(filterStudents(rows, { risk: "1" }).map((r) => r.id)).toEqual([1]);
    expect(filterStudents(rows, { risk: "" })).toHaveLength(3);
    expect(filterStudents(rows, { risk: "1", course: "Physics" })).toHaveLength(0);
  });
  it("combines filters with AND", () => {
    expect(filterStudents(rows, { course: "Math", max: "60" }).map((r) => r.id)).toEqual([1]);
  });
});

describe("sortStudents", () => {
  it("sorts text case-insensitively", () => {
    expect(sortStudents(rows, { key: "name", direction: "asc" }).map((r) => r.id)).toEqual([1, 2, 3]);
  });
  it("sorts numbers numerically and keeps missing values last in both directions", () => {
    expect(sortStudents(rows, { key: "score", direction: "asc" }).map((r) => r.id)).toEqual([1, 2, 3]);
    expect(sortStudents(rows, { key: "score", direction: "desc" }).map((r) => r.id)).toEqual([2, 1, 3]);
  });
  it("does not mutate the input and returns it untouched without a key", () => {
    const copy = [...rows];
    sortStudents(rows, { key: "score", direction: "desc" });
    expect(rows).toEqual(copy);
    expect(sortStudents(rows, { key: null, direction: "asc" })).toBe(rows);
  });
});

describe("paginate", () => {
  const items = Array.from({ length: 55 }, (_, i) => i);
  it("slices a page", () => {
    const p = paginate(items, 2, 25);
    expect(p.items).toHaveLength(25);
    expect(p.start).toBe(25);
    expect(p.pageCount).toBe(3);
  });
  it("clamps out-of-range pages", () => {
    expect(paginate(items, 99, 25).page).toBe(3);
    expect(paginate(items, 0, 25).page).toBe(1);
  });
  it("handles an empty list", () => {
    const p = paginate([], 1, 25);
    expect(p.pageCount).toBe(1);
    expect(p.total).toBe(0);
  });
});

describe("aggregations", () => {
  it("lists distinct values in order", () => {
    expect(distinctValues(rows, "semester")).toEqual(["2024-1", "2024-2"]);
  });
  it("averages GPA per semester, oldest first", () => {
    expect(gpaBySemester(rows)).toEqual([
      { semester: "2024-1", gpa: 0 },
      { semester: "2024-2", gpa: 3 },
    ]);
  });
  it("averages score per course, hardest first, ignoring missing scores", () => {
    expect(courseAverages(rows)).toEqual([
      { course: "Math", avgScore: 55, students: 1 },
      { course: "Physics", avgScore: 91, students: 1 },
    ]);
  });
});
