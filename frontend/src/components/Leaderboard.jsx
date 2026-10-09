import { Link } from "react-router-dom";
import AsyncCard from "./AsyncCard";
import { useFetch } from "../hooks/useFetch";

function Leaderboard() {
  const { data, loading, error, refetch } = useFetch("/api/top-students");
  const leaders = data ?? [];

  return (
    <AsyncCard title="Top students" loading={loading} error={error} onRetry={refetch}>
      {leaders.length === 0 ? (
        <p className="state">No student data yet.</p>
      ) : (
        <ol>
          {leaders.map((student) => (
            <li key={student.id}>
              <Link to={`/students/${student.id}`}>{student.name}</Link>{" "}
              <span className="muted">GPA {student.gpa}</span>
            </li>
          ))}
        </ol>
      )}
    </AsyncCard>
  );
}

export default Leaderboard;
