import { describe, it, expect } from "vitest";
import { kindLabel, formatDate, excerpt } from "./interventions";
import { validateIntervention } from "./validate";
import { roleLabel } from "./roles";

describe("kindLabel", () => {
  it("shows a readable name and falls back to the raw value", () => {
    expect(kindLabel("parent_contact")).toBe("Parent or guardian contact");
    expect(kindLabel("mystery")).toBe("mystery");
  });
});

describe("formatDate", () => {
  it("formats dates and timestamps in UTC", () => {
    expect(formatDate("2026-10-12")).toBe("12 Oct 2026");
    expect(formatDate("2026-10-12 23:30:00")).toBe("12 Oct 2026");
  });
  it("handles empty and invalid values", () => {
    expect(formatDate(null)).toBe("");
    expect(formatDate("not a date")).toBe("not a date");
  });
});

describe("excerpt", () => {
  it("keeps short notes whole and flattens line breaks", () => {
    expect(excerpt("Line one\nLine two")).toBe("Line one Line two");
  });
  it("shortens long notes at a word boundary", () => {
    const text = "word ".repeat(60);
    const out = excerpt(text, 50);
    expect(out.endsWith("…")).toBe(true);
    expect(out.length <= 51).toBe(true);
    expect(out.includes("wor…")).toBe(false);
  });
});

describe("validateIntervention", () => {
  it("requires a note and a sensible date", () => {
    expect(validateIntervention({ note: "Met the student", due: "" })).toEqual({});
    expect(validateIntervention({ note: "Met", due: "2026-10-12" })).toEqual({});
    expect(Object.keys(validateIntervention({ note: "  ", due: "" }))).toEqual(["note"]);
    expect(Object.keys(validateIntervention({ note: "x".repeat(1001), due: "" }))).toEqual(["note"]);
    expect(Object.keys(validateIntervention({ note: "ok", due: "12/10/2026" }))).toEqual(["due"]);
  });
});

describe("roleLabel", () => {
  it("names each role", () => {
    expect(roleLabel("admin")).toBe("Administrator");
    expect(roleLabel("staff")).toBe("Staff");
    expect(roleLabel("viewer")).toBe("Viewer");
  });
});
