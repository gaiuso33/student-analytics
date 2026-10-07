import { describe, it, expect } from "vitest";
import { gradeFor, gradeDistribution, isValidScore } from "./grades";

describe("gradeFor", () => {
  it("uses the A-F boundaries", () => {
    const cases = [[100, "A"], [90, "A"], [89, "B"], [80, "B"], [79, "C"], [70, "C"], [69, "D"], [60, "D"], [59, "F"], [0, "F"]];
    cases.forEach(([score, grade]) => expect(gradeFor(score)).toBe(grade));
  });
});

describe("isValidScore", () => {
  it("accepts finite numbers only", () => {
    expect(isValidScore(0)).toBe(true);
    expect(isValidScore(null)).toBe(false);
    expect(isValidScore(undefined)).toBe(false);
    expect(isValidScore("80")).toBe(false);
    expect(isValidScore(NaN)).toBe(false);
  });
});

describe("gradeDistribution", () => {
  it("counts each grade and skips invalid scores", () => {
    const result = gradeDistribution([{ score: 95 }, { score: 91 }, { score: 55 }, { score: null }, {}]);
    expect(result).toEqual([
      { grade: "A", students: 2 },
      { grade: "B", students: 0 },
      { grade: "C", students: 0 },
      { grade: "D", students: 0 },
      { grade: "F", students: 1 },
    ]);
  });
});
