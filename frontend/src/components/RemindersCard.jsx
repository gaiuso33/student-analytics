import { Link } from "react-router-dom";
import AsyncCard from "./AsyncCard";
import { useFetch } from "../hooks/useFetch";
import { kindLabel } from "../utils/interventions";
import { dueLabel } from "../utils/reminders";

/** "Your follow-ups": what is assigned to me and overdue or due soon. Shown to staff and administrators. */
function RemindersCard() {
  const { data, loading, error, refetch } = useFetch("/api/reminders");
  const mine = data?.mine;
  const team = data?.team;
  const needAttention = mine ? mine.overdue + mine.due_soon : 0;

  return (
    <AsyncCard title="Your follow-ups" loading={loading} error={error} onRetry={refetch} className="card--wide">
      {mine && needAttention === 0 && (
        <p className="state">
          Nothing of yours is overdue or due in the next {data.days_ahead} days.
          {mine.open > 0 ? ` You have ${mine.open} open in total.` : ""}
        </p>
      )}
      {mine && needAttention > 0 && (
        <>
          <p className="reminder-counts">
            <span className={mine.overdue > 0 ? "reminder-counts__alert" : ""}><strong>{mine.overdue}</strong> overdue</span>
            <span><strong>{mine.due_soon}</strong> due soon</span>
          </p>
          <ul className="plain-list">
            {mine.items.map((item) => (
              <li key={item.id}>
                <Link to={`/students/${item.student_id}`}>{item.student_name}</Link>{" "}
                <span className="muted">{kindLabel(item.kind)}: {dueLabel(item)}</span>
              </li>
            ))}
          </ul>
          {needAttention > mine.items.length && <p className="muted">and {needAttention - mine.items.length} more</p>}
        </>
      )}
      {mine && (
        <p className="card__footer">
          <Link to="/interventions?show=mine">See all my follow-ups</Link>
          {team?.unattended_at_risk > 0 && (
            <>
              {" "}
              <Link to="/interventions">
                {team.unattended_at_risk} at-risk {team.unattended_at_risk === 1 ? "student has" : "students have"} no follow-up
              </Link>
            </>
          )}
        </p>
      )}
    </AsyncCard>
  );
}

export default RemindersCard;
