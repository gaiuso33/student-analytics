import { useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import Filters from "../components/Filters";
import Pagination from "../components/Pagination";
import StudentTable from "../components/StudentTable";
import { useAuth } from "../auth/useAuth";
import { useFetch } from "../hooks/useFetch";
import { downloadCsv, studentsToCsv } from "../utils/csv";
import { distinctValues, filterStudents, paginate, sortStudents } from "../utils/students";
import { PAGE_SIZES, readView, toQuery } from "../utils/viewState";

function StudentsPage() {
  const { isAdmin } = useAuth();
  const { data, loading, error, refetch } = useFetch("/api/students");
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const all = data ?? [];

  // The view (filters, sort, page) is kept in this component's own state so every control reacts at once.
  // The page address is a mirror of it, so filtered views can still be bookmarked and shared.
  // (Reading the values back from the address on every change made controls snap back and drop typed
  // characters, because the router applies address changes a moment late.)
  const [view, setView] = useState(() => readView(params));
  const [seenKey, setSeenKey] = useState(location.key);
  if (location.key !== seenKey) {
    // The address changed. If it was not our own mirror write (a link or the sidebar sent us here), follow it.
    setSeenKey(location.key);
    if (!location.state?.mirror) setView(readView(params));
  }

  function change(patch, { resetPage = true } = {}) {
    const next = { ...view, ...patch, ...(resetPage ? { page: 1 } : {}) };
    setView(next);
    setParams(toQuery(next), { replace: true, state: { mirror: true } });
  }

  const filters = {
    search: view.search,
    course: view.course,
    semester: view.semester,
    min: view.min,
    max: view.max,
    risk: view.risk,
  };
  const sortConfig = { key: view.sort || null, direction: view.dir };
  const { page, size } = view;

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
            onChange={(patch) => change(patch)}
            courses={courses}
            semesters={semesters}
            resultCount={filtered.length}
            totalCount={all.length}
          />
          <StudentTable
            students={paged.items}
            sortConfig={sortConfig}
            setSortConfig={({ key, direction }) => change({ sort: key, dir: direction }, { resetPage: false })}
          />
          <Pagination
            page={paged.page}
            pageCount={paged.pageCount}
            total={paged.total}
            start={paged.start}
            size={size}
            sizes={PAGE_SIZES}
            onPage={(p) => change({ page: p }, { resetPage: false })}
            onSize={(s) => change({ size: s })}
          />
        </>
      )}
    </div>
  );
}

export default StudentsPage;
