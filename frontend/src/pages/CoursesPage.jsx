import { Link } from "react-router-dom";
import AsyncCard from "../components/AsyncCard";
import { useFetch } from "../hooks/useFetch";
import { formatNumber } from "../utils/students";
import { PASS_MARK } from "../utils/grades";

function CoursesPage() {
  const { data, loading, error, refetch } = useFetch("/api/courses");
  const courses = data ?? [];

  return (
    <div className="page">
      <header className="page-header">
        <h1>Courses</h1>
      </header>

      <AsyncCard title="Courses, hardest first" loading={loading} error={error} onRetry={refetch}>
        {courses.length === 0 ? (
          <p className="state">No course data yet.</p>
        ) : (
          <div className="table-wrap table-wrap--flat">
            <table>
              <thead>
                <tr>
                  <th>Course</th>
                  <th>Average score</th>
                  <th>Pass rate (score ≥ {PASS_MARK})</th>
                  <th>Students</th>
                  <th><span className="visually-hidden">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {courses.map((c) => (
                  <tr key={c.course}>
                    <td>{c.course}</td>
                    <td>{formatNumber(Number(c.average_score), 1)}</td>
                    <td>{formatNumber(Number(c.pass_rate), 1)}%</td>
                    <td>{c.students}</td>
                    <td>
                      <Link to={`/students?course=${encodeURIComponent(c.course)}`}>
                        View records<span className="visually-hidden"> for {c.course}</span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AsyncCard>
    </div>
  );
}

export default CoursesPage;
