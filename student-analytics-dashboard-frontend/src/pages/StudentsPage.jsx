import { Link, useSearchParams } from "react-router-dom";
import Filters from "../components/Filters";
import Pagination from "../components/Pagination";
import StudentTable from "../components/StudentTable";
import { useAuth } from "../auth/useAuth";
import { useFetch } from "../hooks/useFetch";
import { downloadCsv, studentsToCsv } from "../utils/csv";
import { distinctValues, filterStudents, paginate, sortStudents } from "../utils/students";

const PAGE_SIZES = [10, 25, 50, 100];
const DEFAULT_SIZE = 25;

function StudentsPage() {
  const { isAdmin } = useAuth();
  const { data, loading, error, refetch } = useFetch("/api/students");
  const [params, setParams] = useSearchParams();
  const all = data ?? [];

  // All view state lives in the URL, so filtered views can be bookmarked and shared.
  const filters = {
    search: params.get("search") ?? "",
    course: params.get("course") ?? "",
    semester: params.get("semester") ?? "",
    min: params.get("min") ?? "",
    max: params.get("max") ?? "",
    risk: params.get("risk") === "1" ? "1" : "",
  };
  const sortConfig = {
    key: params.get("sort"),
    direction: params.get("dir") === "desc" ? "desc" : "asc",
  };
  const sizeParam = Number(params.get("size"));
  const size = PAGE_SIZES.includes(sizeParam) ? sizeParam : DEFAULT_SIZE;
  const page = Math.max(1, Number(params.get("page")) || 1);

  function update(patch, { resetPage = true } = {}) {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        Object.entries(patch).forEach(([key, value]) => {
          if (value === "" || value === null || value === undefined) next.delete(key);
          else next.set(key, String(value));
        });
        if (resetPage) next.delete("page");
        return next;
      },
      { replace: true }
    );
  }

  const courses = distinctValues(all, "course");
  const semesters = distinctValues(all, "semester");
  const filtered = filterStudents(all, filters);
  const sorted = sortStudents(filtered, sortConfig);
  const paged = paginate(sorted, page, size);

  function handleExport() {
    // Exports every row matching the current filters and sort, not just the visible page.
    const date = new Date().toISOString().slice(0, 10);
    downloadCsv(`student-records-${date}.csv`, studentsToCsv(sorted));
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Students</h1>
        <div className="page-header__actions">
          {isAdmin && <Link to="/admin/import" className="button-link button-link--ghost">Import CSV</Link>}
          {isAdmin && <Link to="/students/new" className="button-link">Add student</Link>}
          <button type="button" className="button--ghost" onClick={handleExport} disabled={!data || sorted.length === 0}>
            Export CSV ({sorted.length})
          </button>
        </div>
      </header>

      {loading && <p className="state">Loading student records…</p>}
      {error && (
        <div className="state state--error" role="alert">
          <p>{error.message}</p>
          <button type="button" onClick={refetch}>Try again</button>
        </div>
      )}

      {data && (
        <>
          <Filters
            filters={filters}
            onChange={(patch) => update(patch)}
            courses={courses}
            semesters={semesters}
            resultCount={filtered.length}
            totalCount={all.length}
          />
          <StudentTable
            students={paged.items}
            sortConfig={sortConfig}
            setSortConfig={({ key, direction }) => update({ sort: key, dir: direction }, { resetPage: false })}
          />
          <Pagination
            page={paged.page}
            pageCount={paged.pageCount}
            total={paged.total}
            start={paged.start}
            size={size}
            sizes={PAGE_SIZES}
            onPage={(p) => update({ page: p }, { resetPage: false })}
            onSize={(s) => update({ size: s === DEFAULT_SIZE ? "" : s })}
          />
        </>
      )}
    </div>
  );
}

export default StudentsPage;
