import { Link } from "react-router-dom";
import AsyncCard from "./AsyncCard";
import { useFetch } from "../hooks/useFetch";
import { formatNumber } from "../utils/students";

function CourseDifficulty() {
  const { data, loading, error, refetch } = useFetch("/api/course-difficulty");
  const hardest = [...(data ?? [])]
    .sort((a, b) => a.average_score - b.average_score)
    .slice(0, 5);

  return (
    <AsyncCard title="Hardest courses" loading={loading} error={error} onRetry={refetch}>
      {hardest.length === 0 ? (
        <p className="state">No course data yet.</p>
      ) : (
        <ol>
          {hardest.map((course) => (
            <li key={course.course}>
              <Link to={`/students?course=${encodeURIComponent(course.course)}`}>{course.course}</Link>{" "}
              <span className="muted">avg {formatNumber(Number(course.average_score), 1)}</span>
            </li>
          ))}
        </ol>
      )}
    </AsyncCard>
  );
}

export default CourseDifficulty;
