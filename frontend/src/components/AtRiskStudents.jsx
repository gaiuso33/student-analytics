import { Link } from "react-router-dom";
import AsyncCard from "./AsyncCard";
import { useFetch } from "../hooks/useFetch";

const PREVIEW = 8;

function AtRiskStudents() {
  const { data, loading, error, refetch } = useFetch("/api/at-risk-students");
  const students = data ?? [];
  const shown = students.slice(0, PREVIEW);

  return (
    <AsyncCard title="At-risk students" loading={loading} error={error} onRetry={refetch} className="card--alert">
      {students.length === 0 ? (
        <p className="state">No students are currently at risk.</p>
      ) : (
        <>
          <ul>
            {shown.map((student) => (
              <li key={student.id}>
                <Link to={`/students/${student.id}`}>{student.name}</Link>{" "}
                <span className="muted">GPA {student.gpa}</span>
                {student.open_interventions === 0 && (
                  <span className="badge badge--alert badge--small">No follow-up</span>
                )}
              </li>
            ))}
          </ul>
          <p className="card__footer">
            {students.length > PREVIEW && <span className="muted">and {students.length - PREVIEW} more. </span>}
            <Link to="/students?risk=1">See all at-risk records</Link>{" "}
            <Link to="/interventions">Review follow-ups</Link>
          </p>
        </>
      )}
    </AsyncCard>
  );
}

export default AtRiskStudents;
