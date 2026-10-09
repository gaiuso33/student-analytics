import { describe, it, expect } from "vitest";
import { escapeCell, toCsv, studentsToCsv } from "./csv";

describe("escapeCell", () => {
  it("leaves plain values alone and blanks null", () => {
    expect(escapeCell("Ada")).toBe("Ada");
    expect(escapeCell(42)).toBe("42");
    expect(escapeCell(null)).toBe("");
    expect(escapeCell(undefined)).toBe("");
  });
  it("quotes commas, quotes and newlines", () => {
    expect(escapeCell("Eze, Ada")).toBe('"Eze, Ada"');
    expect(escapeCell('say "hi"')).toBe('"say ""hi"""');
    expect(escapeCell("a\nb")).toBe('"a\nb"');
  });
  it("neutralises spreadsheet formulas in text but not negative numbers", () => {
    expect(escapeCell("=SUM(A1:A2)")).toBe("'=SUM(A1:A2)");
    expect(escapeCell("@cmd")).toBe("'@cmd");
    expect(escapeCell(-5)).toBe("-5");
  });
});

describe("toCsv", () => {
  it("writes a header and one line per row", () => {
    const csv = toCsv([{ a: 1, b: "x" }], [
      { header: "A", value: (r) => r.a },
      { header: "B", value: (r) => r.b },
    ]);
    expect(csv).toBe("A,B\r\n1,x");
  });
});

describe("studentsToCsv", () => {
  it("adds a letter grade and leaves it blank for missing scores", () => {
    const csv = studentsToCsv([
      { name: "Ada", course: "Math", semester: "2024-1", score: 91, gpa: 4, at_risk: false },
      { name: "Bola", course: "Math", semester: "2024-1", score: null, gpa: 2, at_risk: true },
    ]);
    const lines = csv.split("\r\n");
    expect(lines[0]).toBe("Student,Course,Semester,Score,Grade,GPA,At risk");
    expect(lines[1]).toBe("Ada,Math,2024-1,91,A,4,No");
    expect(lines[2]).toBe("Bola,Math,2024-1,,,2,Yes");
  });
});
