import { Link, useParams } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import ChartCard from "../components/ChartCard";
import { useFetch } from "../hooks/useFetch";
import { gradeFor } from "../utils/grades";
import { formatNumber } from "../utils/students";

function StudentDetailPage() {
  const { id } = useParams();
  const { data: student, loading, error, refetch } = useFetch(`/api/students/${encodeURIComponent(id)}`);

  return (
    <div className="page">
      <p><Link to="/students">Back to students</Link></p>

      {loading && <p className="state">Loading student…</p>}

      {error && (
        <div className="state state--error" role="alert">
          <p>{error.status === 404 ? "This student could not be found." : error.message}</p>
          {error.status !== 404 && <button type="button" onClick={refetch}>Try again</button>}
        </div>
      )}

      {student && (
        <>
          <header className="page-header">
            <h1>{student.name}</h1>
            <span className={`badge ${student.at_risk ? "badge--alert" : "badge--ok"}`}>
              {student.at_risk ? "At risk" : "On track"}
            </span>
          </header>

          <div className="stats-grid">
            <div className="card card--stat"><h3>Cumulative GPA</h3><p>{formatNumber(student.gpa)}</p></div>
            <div className="card card--stat"><h3>Courses taken</h3><p>{student.records.length}</p></div>
            <div className="card card--stat"><h3>Failing results</h3><p>{student.failing_courses}</p></div>
          </div>

          <div className="charts">
            <ChartCard title="GPA by semester" empty={student.semester_gpa.length < 2}>
              <LineChart data={student.semester_gpa} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="semester" />
                <YAxis domain={[0, 4]} />
                <Tooltip />
                <Line type="monotone" dataKey="gpa" name="GPA" stroke="var(--chart-line)" strokeWidth={2} dot />
              </LineChart>
            </ChartCard>
          </div>

          <h2>Results</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Semester</th><th>Course</th><th>Score</th><th>Grade</th></tr>
              </thead>
              <tbody>
                {student.records.map((r) => (
                  <tr key={r.id}>
                    <td>{r.semester}</td>
                    <td>{r.course}</td>
                    <td>{r.score}</td>
                    <td>{gradeFor(r.score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export default StudentDetailPage;
