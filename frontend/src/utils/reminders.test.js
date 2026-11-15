import { describe, it, expect } from "vitest";
import { attentionCount, dueLabel } from "./reminders";

const open = { status: "open", due_date: "2026-10-13", overdue: false, due_soon: false, due_in_days: 20 };

describe("dueLabel", () => {
  it("describes overdue, due today, tomorrow, soon and later", () => {
    expect(dueLabel({ ...open, overdue: true, due_in_days: -3 })).toBe("Overdue, was due 13 Oct 2026");
    expect(dueLabel({ ...open, due_soon: true, due_in_days: 0 })).toBe("Due today (13 Oct 2026)");
    expect(dueLabel({ ...open, due_soon: true, due_in_days: 1 })).toBe("Due tomorrow (13 Oct 2026)");
    expect(dueLabel({ ...open, due_soon: true, due_in_days: 2 })).toBe("Due in 2 days (13 Oct 2026)");
    expect(dueLabel(open)).toBe("Due 13 Oct 2026");
  });
  it("says nothing for finished or undated items", () => {
    expect(dueLabel({ ...open, status: "done" })).toBe("");
    expect(dueLabel({ ...open, due_date: null })).toBe("");
  });
});

describe("attentionCount", () => {
  it("adds my overdue and due-soon items", () => {
    expect(attentionCount({ mine: { overdue: 2, due_soon: 3, open: 9 } })).toBe(5);
  });
  it("is zero when there is no data yet", () => {
    expect(attentionCount(null)).toBe(0);
    expect(attentionCount({})).toBe(0);
  });
});
