import { Link } from "react-router-dom";

const COLUMNS = [
  { key: "name", label: "Name" },
  { key: "course", label: "Course" },
  { key: "score", label: "Score" },
  { key: "semester", label: "Semester" },
  { key: "gpa", label: "GPA" },
];

function StudentTable({ students, sortConfig, setSortConfig }) {
  function handleSort(key) {
    const direction =
      sortConfig.key === key && sortConfig.direction === "asc" ? "desc" : "asc";
    setSortConfig({ key, direction });
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {COLUMNS.map(({ key, label }) => {
              const active = sortConfig.key === key;
              return (
                <th
                  key={key}
                  aria-sort={active ? (sortConfig.direction === "asc" ? "ascending" : "descending") : "none"}
                >
                  <button type="button" className="th-button" onClick={() => handleSort(key)}>
                    {label} {active ? (sortConfig.direction === "asc" ? "↑" : "↓") : ""}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {students.length === 0 ? (
            <tr>
              <td colSpan={COLUMNS.length} className="state">
                No records match these filters. Try widening the score range or clearing the filters.
              </td>
            </tr>
          ) : (
            students.map((s, i) => (
              <tr key={s.id ?? `${s.name}-${s.course}-${i}`}>
                <td>
                  {s.student_id !== undefined ? (
                    <Link to={`/students/${s.student_id}`}>{s.name}</Link>
                  ) : (
                    s.name
                  )}
                  {s.at_risk && <span className="badge badge--alert badge--small">At risk</span>}
                </td>
                <td>{s.course}</td>
                <td>{s.score}</td>
                <td>{s.semester}</td>
                <td>{s.gpa}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default StudentTable;
