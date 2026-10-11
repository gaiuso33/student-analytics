import { useState } from "react";
import AsyncCard from "./AsyncCard";
import InterventionForm from "./InterventionForm";
import { request } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { useFetch } from "../hooks/useFetch";
import { formatDate, kindLabel } from "../utils/interventions";

function Item({ item, canRecord, isAdmin, onToggle, onEdit, onDelete }) {
  const done = item.status === "done";
  return (
    <li className={`followup${done ? " followup--done" : ""}`}>
      <div className="followup__head">
        <span className="badge badge--neutral">{kindLabel(item.kind)}</span>
        {done ? (
          <span className="badge badge--ok">Done {formatDate(item.completed_at)}</span>
        ) : item.overdue ? (
          <span className="badge badge--alert">Overdue, was due {formatDate(item.due_date)}</span>
        ) : item.due_date ? (
          <span className="muted">Due {formatDate(item.due_date)}</span>
        ) : null}
      </div>
      <p className="followup__note">{item.note}</p>
      <p className="muted followup__meta">
        Added by {item.created_by ?? "unknown"} on {formatDate(item.created_at)}
      </p>
      {canRecord && (
        <div className="followup__actions">
          <button type="button" className="button--ghost button--small" onClick={() => onToggle(item)}>
            {done ? "Reopen" : "Mark done"}
          </button>
          <button type="button" className="button--ghost button--small" onClick={() => onEdit(item)}>
            Edit
          </button>
          {isAdmin && (
            <button type="button" className="button--ghost button--small button--danger" onClick={() => onDelete(item)}>
              Delete
            </button>
          )}
        </div>
      )}
    </li>
  );
}

/** Follow-ups for one student: everyone signed in can read, staff and administrators can record. */
function InterventionsPanel({ studentId, atRisk }) {
  const { canRecord, isAdmin } = useAuth();
  const { data, loading, error, refetch } = useFetch(`/api/students/${studentId}/interventions`);
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [actionError, setActionError] = useState("");

  const items = data ?? [];
  const open = items.filter((i) => i.status === "open");
  const done = items.filter((i) => i.status === "done");

  async function run(action) {
    setActionError("");
    try {
      await action();
      refetch();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function add(values) {
    await request(`/api/students/${studentId}/interventions`, { method: "POST", body: values });
    setAdding(false);
    refetch();
  }

  async function save(id, values) {
    await request(`/api/interventions/${id}`, { method: "PATCH", body: values });
    setEditingId(null);
    refetch();
  }

  const toggle = (item) =>
    run(() => request(`/api/interventions/${item.id}`, { method: "PATCH", body: { status: item.status === "done" ? "open" : "done" } }));

  const remove = (item) => {
    if (!window.confirm("Delete this follow-up? This can't be undone.")) return;
    run(() => request(`/api/interventions/${item.id}`, { method: "DELETE" }));
  };

  const list = (entries) => (
    <ul className="followups">
      {entries.map((item) =>
        editingId === item.id ? (
          <li key={item.id} className="followup">
            <InterventionForm
              initial={item}
              submitLabel="Save changes"
              onSubmit={(values) => save(item.id, values)}
              onCancel={() => setEditingId(null)}
            />
          </li>
        ) : (
          <Item
            key={item.id}
            item={item}
            canRecord={canRecord}
            isAdmin={isAdmin}
            onToggle={toggle}
            onEdit={(i) => setEditingId(i.id)}
            onDelete={remove}
          />
        )
      )}
    </ul>
  );

  return (
    <AsyncCard title="Follow-ups" loading={loading} error={error} onRetry={refetch} className="card--wide">
      {atRisk && open.length === 0 && (
        <p className="notice notice--warning" role="status">
          This student is at risk and has no open follow-up.
        </p>
      )}
      {actionError && <p className="state state--error" role="alert">{actionError}</p>}

      {canRecord && !adding && (
        <p>
          <button type="button" className="button--small" onClick={() => setAdding(true)}>Add follow-up</button>
        </p>
      )}
      {adding && (
        <div className="followup followup--new">
          <InterventionForm submitLabel="Add follow-up" onSubmit={add} onCancel={() => setAdding(false)} />
        </div>
      )}

      {items.length === 0 && !adding && <p className="state">No follow-ups recorded yet.</p>}
      {open.length > 0 && (<><h3 className="followups__heading">Open ({open.length})</h3>{list(open)}</>)}
      {done.length > 0 && (<><h3 className="followups__heading">Done ({done.length})</h3>{list(done)}</>)}
    </AsyncCard>
  );
}

export default InterventionsPanel;
