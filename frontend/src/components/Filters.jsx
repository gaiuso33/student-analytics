const FIELDS = ["search", "course", "semester", "min", "max", "risk"];

function Filters({ filters, onChange, courses, semesters, resultCount, totalCount }) {
  const active = FIELDS.some((f) => filters[f] !== "");

  return (
    <form className="filters" onSubmit={(e) => e.preventDefault()} role="search">
      <div className="filters__field filters__field--wide">
        <label htmlFor="f-search">Search</label>
        <input
          id="f-search"
          type="search"
          placeholder="Name or course"
          value={filters.search}
          onChange={(e) => onChange({ search: e.target.value })}
        />
      </div>

      <div className="filters__field">
        <label htmlFor="f-course">Course</label>
        <select id="f-course" value={filters.course} onChange={(e) => onChange({ course: e.target.value })}>
          <option value="">All courses</option>
          {courses.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="filters__field">
        <label htmlFor="f-semester">Semester</label>
        <select id="f-semester" value={filters.semester} onChange={(e) => onChange({ semester: e.target.value })}>
          <option value="">All semesters</option>
          {semesters.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="filters__field filters__field--narrow">
        <label htmlFor="f-min">Min score</label>
        <input id="f-min" type="number" min="0" max="100" inputMode="numeric" value={filters.min}
          onChange={(e) => onChange({ min: e.target.value })} />
      </div>

      <div className="filters__field filters__field--narrow">
        <label htmlFor="f-max">Max score</label>
        <input id="f-max" type="number" min="0" max="100" inputMode="numeric" value={filters.max}
          onChange={(e) => onChange({ max: e.target.value })} />
      </div>

      <div className="filters__check">
        <input id="f-risk" type="checkbox" checked={filters.risk === "1"}
          onChange={(e) => onChange({ risk: e.target.checked ? "1" : "" })} />
        <label htmlFor="f-risk">At-risk students only</label>
      </div>

      <div className="filters__summary">
        <span className="muted" aria-live="polite">Showing {resultCount} of {totalCount}</span>
        {active && (
          <button type="button" className="button--ghost"
            onClick={() => onChange(Object.fromEntries(FIELDS.map((f) => [f, ""])))}>
            Clear filters
          </button>
        )}
      </div>
    </form>
  );
}

export default Filters;
