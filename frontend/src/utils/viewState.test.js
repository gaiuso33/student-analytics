import { describe, it, expect } from "vitest";
import { readView, toQuery } from "./viewState";

const q = (text) => new URLSearchParams(text);
const canonical = (params) => [...params.entries()].map((e) => e.join("=")).sort().join("&");

describe("readView", () => {
  it("has sensible defaults for an empty address", () => {
    expect(readView(q(""))).toEqual({
      search: "", course: "", semester: "", min: "", max: "", risk: "", sort: "", dir: "asc", page: 1, size: 25,
    });
  });
  it("reads every field", () => {
    const view = readView(q("search=ann&course=Math&semester=2025-1&min=10&max=59&risk=1&sort=score&dir=desc&page=3&size=50"));
    expect(view.search).toBe("ann");
    expect(view.max).toBe("59");
    expect(view.risk).toBe("1");
    expect(view.sort).toBe("score");
    expect(view.dir).toBe("desc");
    expect(view.page).toBe(3);
    expect(view.size).toBe(50);
  });
  it("sanitises nonsense instead of trusting it", () => {
    const view = readView(q("size=7&page=-3&dir=sideways&risk=yes"));
    expect(view.size).toBe(25);
    expect(view.page).toBe(1);
    expect(view.dir).toBe("asc");
    expect(view.risk).toBe("");
    expect(readView(q("page=abc")).page).toBe(1);
    expect(readView(q("page=2.9")).page).toBe(2);
  });
});

describe("toQuery", () => {
  it("leaves out everything at its default", () => {
    expect(toQuery(readView(q(""))).toString()).toBe("");
  });
  it("only writes the direction when there is a sort", () => {
    expect(toQuery({ ...readView(q("")), dir: "desc" }).toString()).toBe("");
    expect(canonical(toQuery({ ...readView(q("")), sort: "name", dir: "desc" }))).toBe("dir=desc&sort=name");
  });
  it("round-trips a full address", () => {
    const text = "course=Math&max=59&min=10&page=2&risk=1&search=ann&semester=2025-1&size=10&sort=score&dir=desc";
    expect(canonical(toQuery(readView(q(text))))).toBe(canonical(q(text)));
  });
  it("encodes awkward text safely", () => {
    const params = toQuery({ ...readView(q("")), search: "a&b=c d" });
    expect(readView(q(params.toString())).search).toBe("a&b=c d");
  });
});
