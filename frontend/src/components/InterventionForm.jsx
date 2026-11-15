import { useId, useState } from "react";
import { useAuth } from "../auth/useAuth";
import { useFetch } from "../hooks/useFetch";
import { KINDS, NOTE_MAX } from "../utils/interventions";
import { validateIntervention } from "../utils/validate";

/** Add or edit a follow-up. onSubmit({ kind, note, due_date }) may throw an Error to show it. */
function InterventionForm({ initial, submitLabel, onSubmit, onCancel }) {
  const [kind, setKind] = useState(initial?.kind ?? "meeting");
  const [note, setNote] = useState(initial?.note ?? "");
  const [due, setDue] = useState(initial?.due_date ?? "");
  const { user } = useAuth();
  // New follow-ups start assigned to whoever is recording them; editing keeps the current owner.
  const [assignee, setAssignee] = useState(initial ? (initial.assigned_to ?? "") : user.username);
  const { data: people } = useFetch("/api/assignees");
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [pending, setPending] = useState(false);
  const uid = useId();

  // The current owner is always listed, even if they are no longer active or the list hasn't loaded yet.
  const assigneeNames = [...new Set([...(people ?? []).map((p) => p.username), ...(assignee ? [assignee] : [])])];

  async function handleSubmit(e) {
    e.preventDefault();
    const found = validateIntervention({ note, due });
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setServerError("");
    setPending(true);
    try {
      await onSubmit({ kind, note: note.trim(), due_date: due || null, assigned_to: assignee || null });
    } catch (err) {
      setServerError(err.message);
      setPending(false);
    }
  }

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <div className="form__row">
        <div className="field">
          <label htmlFor={`${uid}-kind`}>Type</label>
          <select id={`${uid}-kind`} value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${uid}-due`}>Due date (optional)</label>
          <input
            id={`${uid}-due`}
            type="date"
            value={due}
            onChange={(e) => setDue(e.target.value)}
            aria-invalid={Boolean(errors.due)}
          />
          {errors.due && <p className="field__error" role="alert">{errors.due}</p>}
        </div>
      </div>

      <div className="field">
        <label htmlFor={`${uid}-assignee`}>Assigned to</label>
        <select id={`${uid}-assignee`} value={assignee} onChange={(e) => setAssignee(e.target.value)}>
          <option value="">Nobody (anyone can pick it up)</option>
          {assigneeNames.map((name) => (
            <option key={name} value={name}>{name === user.username ? `${name} (you)` : name}</option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor={`${uid}-note`}>What was done or is planned</label>
        <textarea
          id={`${uid}-note`}
          rows={4}
          maxLength={NOTE_MAX}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          aria-invalid={Boolean(errors.note)}
          aria-describedby={`${uid}-hint`}
        />
        <p id={`${uid}-hint`} className="field__hint">
          {note.length}/{NOTE_MAX}. Keep notes factual and avoid sensitive personal details.
        </p>
        {errors.note && <p className="field__error" role="alert">{errors.note}</p>}
      </div>

      <div className="form__actions form__actions--flush">
        <button type="submit" disabled={pending}>{pending ? "Saving…" : submitLabel}</button>
        <button type="button" className="button--ghost" onClick={onCancel}>Cancel</button>
      </div>
      {serverError && <p className="state state--error" role="alert">{serverError}</p>}
    </form>
  );
}

export default InterventionForm;
