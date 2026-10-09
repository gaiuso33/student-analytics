import { useId, useState } from "react";
import { validateName } from "../utils/validate";

/** One-field form for creating or renaming a student. onSubmit(name) may throw an Error to show it. */
function NameForm({ initial = "", submitLabel, onSubmit, onCancel }) {
  const [name, setName] = useState(initial);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const id = useId();

  async function handleSubmit(e) {
    e.preventDefault();
    const problem = validateName(name, "Student name");
    if (problem) {
      setError(problem);
      return;
    }
    setError("");
    setPending(true);
    try {
      await onSubmit(name.trim());
    } catch (err) {
      setError(err.message);
      setPending(false);
    }
  }

  return (
    <form className="form form--inline" onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label htmlFor={id}>Student name</label>
        <input
          id={id}
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={100}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          autoFocus
        />
        {error && <p id={`${id}-error`} className="field__error" role="alert">{error}</p>}
      </div>
      <div className="form__actions">
        <button type="submit" disabled={pending}>{pending ? "Saving…" : submitLabel}</button>
        {onCancel && <button type="button" className="button--ghost" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}

export default NameForm;
