import { useId, useState } from "react";
import { useFetch } from "../hooks/useFetch";
import { validateClassName, validateName, validateStudentCode } from "../utils/validate";

/** Create or edit a student: name, optional student ID and optional class.
 *  onSubmit(name, { student_code, class_name }) may throw an Error to show it. */
function NameForm({ initial = "", initialCode = "", initialClass = "", submitLabel, onSubmit, onCancel }) {
  const [name, setName] = useState(initial);
  const [code, setCode] = useState(initialCode);
  const [klass, setKlass] = useState(initialClass);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const { data: classes } = useFetch("/api/classes"); // suggestions for the class field
  const id = useId();

  async function handleSubmit(e) {
    e.preventDefault();
    const problem = validateName(name, "Student name") ?? validateStudentCode(code) ?? validateClassName(klass);
    if (problem) {
      setError(problem);
      return;
    }
    setError("");
    setPending(true);
    try {
      await onSubmit(name.trim(), { student_code: code.trim() || null, class_name: klass.trim() || null });
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
      </div>
      <div className="field">
        <label htmlFor={`${id}-code`}>Student ID (optional)</label>
        <input id={`${id}-code`} value={code} onChange={(e) => setCode(e.target.value)} maxLength={30} placeholder="e.g. ADM-0123" />
      </div>
      <div className="field">
        <label htmlFor={`${id}-class`}>Class (optional)</label>
        <input id={`${id}-class`} value={klass} onChange={(e) => setKlass(e.target.value)} maxLength={40} list={`${id}-classes`} placeholder="e.g. JSS 2A" />
        <datalist id={`${id}-classes`}>
          {(classes ?? []).map((c) => <option key={c.name} value={c.name} />)}
        </datalist>
      </div>
      <div className="form__actions">
        <button type="submit" disabled={pending}>{pending ? "Saving…" : submitLabel}</button>
        {onCancel && <button type="button" className="button--ghost" onClick={onCancel}>Cancel</button>}
      </div>
      {error && <p id={`${id}-error`} className="state state--error form__error" role="alert">{error}</p>}
    </form>
  );
}

export default NameForm;
