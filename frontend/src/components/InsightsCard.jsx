import { Link } from "react-router-dom";
import AsyncCard from "./AsyncCard";
import { useFetch } from "../hooks/useFetch";

const TONE_LABEL = { positive: "Good news", warning: "Needs attention", neutral: "Note" };

function InsightsCard() {
  const { data, loading, error, refetch } = useFetch("/api/insights");
  const insights = data?.insights ?? [];

  return (
    <AsyncCard title="Insights" loading={loading} error={error} onRetry={refetch} className="card--wide">
      {insights.length === 0 ? (
        <p className="state">
          Insights appear once there are results for at least two semesters.
        </p>
      ) : (
        <ul className="insights">
          {insights.map((item) => (
            <li key={item.id} className={`insight insight--${item.tone}`}>
              <span className="insight__tone">{TONE_LABEL[item.tone] ?? "Note"}</span>
              <span className="insight__text">{item.text}</span>
              {item.link && <Link to={item.link}>See the results</Link>}
              {item.students && (
                <ul className="insight__students">
                  {item.students.map((s) => (
                    <li key={s.id}>
                      <Link to={`/students/${s.id}`}>{s.name}</Link>{" "}
                      <span className="muted">{s.detail}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </AsyncCard>
  );
}

export default InsightsCard;
