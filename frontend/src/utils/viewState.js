// The Students page's view (filters, sort, page, page size) and how it maps to the page address.
export const PAGE_SIZES = [10, 25, 50, 100];
export const DEFAULT_SIZE = 25;

/** Read a view from URL search params, sanitising anything unexpected. */
export function readView(params) {
  const size = Number(params.get("size"));
  return {
    search: params.get("search") ?? "",
    course: params.get("course") ?? "",
    semester: params.get("semester") ?? "",
    min: params.get("min") ?? "",
    max: params.get("max") ?? "",
    risk: params.get("risk") === "1" ? "1" : "",
    sort: params.get("sort") ?? "",
    dir: params.get("dir") === "desc" ? "desc" : "asc",
    page: Math.max(1, Math.floor(Number(params.get("page"))) || 1),
    size: PAGE_SIZES.includes(size) ? size : DEFAULT_SIZE,
  };
}

/** Turn a view into search params, leaving out everything that is at its default. */
export function toQuery(view) {
  const query = new URLSearchParams();
  for (const key of ["search", "course", "semester", "min", "max"]) {
    if (view[key] !== "") query.set(key, view[key]);
  }
  if (view.risk === "1") query.set("risk", "1");
  if (view.sort) {
    query.set("sort", view.sort);
    query.set("dir", view.dir);
  }
  if (view.page > 1) query.set("page", String(view.page));
  if (view.size !== DEFAULT_SIZE) query.set("size", String(view.size));
  return query;
}
