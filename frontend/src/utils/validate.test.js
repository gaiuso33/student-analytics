import { describe, it, expect } from "vitest";
import { validateName, validateResult, validatePassword, validateUsername } from "./validate";

describe("validateName", () => {
  it("requires a non-blank name of at most 100 characters", () => {
    expect(validateName("Ada Eze")).toBe(null);
    expect(validateName("   ")).toBe("Name is required");
    expect(validateName("x".repeat(101))).toBe("Name must be at most 100 characters");
  });
});

describe("validateResult", () => {
  const ok = { course: "Math", semester: "2025-1", score: "72.5" };
  it("accepts a valid result", () => {
    expect(validateResult(ok)).toEqual({});
    expect(validateResult({ ...ok, score: "0" })).toEqual({});
    expect(validateResult({ ...ok, score: "100" })).toEqual({});
  });
  it("rejects bad scores", () => {
    ["", "  ", "abc", "-1", "100.1", "Infinity"].forEach((score) => {
      expect(Object.keys(validateResult({ ...ok, score }))).toEqual(["score"]);
    });
  });
  it("rejects missing or overlong text fields", () => {
    expect(Object.keys(validateResult({ ...ok, course: " " }))).toEqual(["course"]);
    expect(Object.keys(validateResult({ ...ok, semester: "x".repeat(21) }))).toEqual(["semester"]);
  });
  it("reports every problem at once", () => {
    expect(Object.keys(validateResult({ course: "", semester: "", score: "" }))).toEqual(["course", "semester", "score"]);
  });
});

describe("validatePassword", () => {
  it("enforces the minimum length", () => {
    expect(validatePassword("short")).toBe("Password must be at least 10 characters");
    expect(validatePassword("long-enough-pw")).toBe(null);
  });
});

describe("validateUsername", () => {
  it("allows letters, digits, dot, dash, underscore (3-32)", () => {
    expect(validateUsername("ada.eze-1_")).toBe(null);
    expect(validateUsername("ab")).not.toBe(null);
    expect(validateUsername("has space")).not.toBe(null);
  });
});
