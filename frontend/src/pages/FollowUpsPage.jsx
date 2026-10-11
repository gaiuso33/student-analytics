import { useState } from "react";
import { Link } from "react-router-dom";
import AsyncCard from "../components/AsyncCard";
import { useFetch } from "../hooks/useFetch";
import { excerpt, formatDate, kindLabel } from "../utils/interventions";

function FollowUpsPage() {
  const followUps = useFetch("/api/interventions?status=open");
  const atRisk = useFetch("/api/at-risk-students");
  const [overdueOnly, setOverdueOnly] = useState(false);

  const all = followUps.data ?? [];
  const shown = overdueOnly ? all.filter((i) => i.overdue) : all;
  const overdueCount = all.filter((i) => i.overdue).length;
  const unattended = (atRisk.data ?? []).filter((s) => s.open_interventions === 0);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Follow-ups</h1>
      </header>

      <AsyncCard
        title={`At-risk students with no open follow-up${atRisk.data ? ` (${unattended.length})` : ""}`}
        loading={atRisk.loading}
        error={atRisk.error}
        onRetry={atRisk.refetch}
        className="card--alert card--wide"
      >
        {unattended.length === 0 ? (
          <p className="state">Every at-risk student has an open follow-up.</p>
        ) : (
          <>
            <p className="state">Open a student to record what is being done to support them.</p>
            <ul className="plain-list">
              {unattended.map((s) => (
                <li key={s.id}>
                  <Link to={`/students/${s.id}`}>{s.name}</Link>{" "}
                  <span className="muted">
                    GPA {s.gpa}
                    {s.last_intervention ? `, last follow-up ${formatDate(s.last_intervention)}` : ", no follow-ups yet"}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </AsyncCard>

      <AsyncCard
        title={`Open follow-ups${followUps.data ? ` (${all.length})` : ""}`}
        loading={followUps.loading}
        error={followUps.error}
        onRetry={followUps.refetch}
        className="card--wide"
      >
        {all.length === 0 ? (
          <p className="state">Nothing open right now.</p>
        ) : (
          <>
            <div className="filters__check">
              <input id="overdue-only" type="checkbox" checked={overdueOnly} onChange={(e) => setOverdueOnly(e.target.checked)} />
              <label htmlFor="overdue-only">Overdue only ({overdueCount})</label>
            </div>
            <div className="table-wrap table-wrap--flat">
              <table>
                <thead>
                  <tr><th>Student</th><th>Type</th><th>Note</th><th>Due</th><th>Added by</th></tr>
                </thead>
                <tbody>
                  {shown.length === 0 && (
                    <tr><td colSpan={5} className="state">No overdue follow-ups.</td></tr>
                  )}
                  {shown.map((i) => (
                    <tr key={i.id}>
                      <td><Link to={`/students/${i.student_id}`}>{i.student_name}</Link></td>
                      <td>{kindLabel(i.kind)}</td>
                      <td>{excerpt(i.note)}</td>
                      <td>
                        {i.due_date ? formatDate(i.due_date) : <span className="muted">No date</span>}
                        {i.overdue && <span className="badge badge--alert badge--small">Overdue</span>}
                      </td>
                      <td>{i.created_by ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </AsyncCard>
    </div>
  );
}

export default FollowUpsPage;
