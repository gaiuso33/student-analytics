import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import ChartCard from "../components/ChartCard";
import InterventionsPanel from "../components/InterventionsPanel";
import NameForm from "../components/NameForm";
import ResultForm from "../components/ResultForm";
import { request } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { useFetch } from "../hooks/useFetch";
import { gradeFor } from "../utils/grades";
import { formatNumber } from "../utils/students";

function StudentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const { data: student, loading, error, refetch } = useFetch(`/api/students/${encodeURIComponent(id)}`);

  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [renaming, setRenaming] = useState(false);
  const [actionError, setActionError] = useState("");

  /** Run a mutation and show any failure in the banner. */
  async function run(action) {
    setActionError("");
    try {
      await action();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function addResult(values) {
    await request(`/api/students/${student.id}/records`, { method: "POST", body: values });
    setAdding(false);
    refetch();
  }

  async function saveResult(recordId, values) {
    await request(`/api/records/${recordId}`, { method: "PUT", body: values });
    setEditingId(null);
    refetch();
  }

  async function rename(name) {
    await request(`/api/students/${student.id}`, { method: "PUT", body: { name } });
    setRenaming(false);
    refetch();
  }

  function removeResult(r) {
    if (!window.confirm(`Delete the ${r.course} (${r.semester}) result for ${student.name}?`)) return;
    run(async () => {
      await request(`/api/records/${r.id}`, { method: "DELETE" });
      refetch();
    });
  }

  function removeStudent() {
    if (!window.confirm(`Delete ${student.name} and all of their results? This can't be undone.`)) return;
    run(async () => {
      await request(`/api/students/${student.id}`, { method: "DELETE" });
      navigate("/students");
    });
  }

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
            <div className="page-header__actions">
              <span className={`badge ${student.at_risk ? "badge--alert" : "badge--ok"}`}>
                {student.at_risk ? "At risk" : "On track"}
              </span>
              {isAdmin && (
                <>
                  <button type="button" className="button--ghost button--small" onClick={() => setRenaming((v) => !v)}>
                    Rename
                  </button>
                  <button type="button" className="button--ghost button--small button--danger" onClick={removeStudent}>
                    Delete student
                  </button>
                </>
              )}
            </div>
          </header>

          {actionError && <p className="state state--error" role="alert">{actionError}</p>}

          {renaming && (
            <section className="card form-card">
              <NameForm initial={student.name} submitLabel="Save name" onSubmit={rename} onCancel={() => setRenaming(false)} />
            </section>
          )}

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

          <InterventionsPanel studentId={student.id} atRisk={student.at_risk} />

          <div className="section-header">
            <h2>Results</h2>
            {isAdmin && !adding && (
              <button type="button" className="button--small" onClick={() => setAdding(true)}>Add result</button>
            )}
          </div>

          {adding && (
            <section className="card form-card">
              <ResultForm submitLabel="Add result" onSubmit={addResult} onCancel={() => setAdding(false)} />
            </section>
          )}

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Semester</th><th>Course</th><th>Score</th><th>Grade</th>
                  {isAdmin && <th><span className="visually-hidden">Actions</span></th>}
                </tr>
              </thead>
              <tbody>
                {student.records.length === 0 && (
                  <tr>
                    <td colSpan={isAdmin ? 5 : 4} className="state">No results recorded yet.</td>
                  </tr>
                )}
                {student.records.map((r) =>
                  editingId === r.id ? (
                    <tr key={r.id}>
                      <td colSpan={5}>
                        <ResultForm
                          initial={r}
                          submitLabel="Save"
                          onSubmit={(values) => saveResult(r.id, values)}
                          onCancel={() => setEditingId(null)}
                        />
                      </td>
                    </tr>
                  ) : (
                    <tr key={r.id}>
                      <td>{r.semester}</td>
                      <td>{r.course}</td>
                      <td>{r.score}</td>
                      <td>{gradeFor(r.score)}</td>
                      {isAdmin && (
                        <td className="row-actions">
                          <button type="button" className="button--ghost button--small" onClick={() => setEditingId(r.id)}>
                            Edit<span className="visually-hidden"> {r.course} {r.semester}</span>
                          </button>
                          <button type="button" className="button--ghost button--small button--danger" onClick={() => removeResult(r)}>
                            Delete<span className="visually-hidden"> {r.course} {r.semester}</span>
                          </button>
                        </td>
                      )}
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export default StudentDetailPage;
