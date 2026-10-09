import { useId, useState } from "react";
import { useFetch } from "../hooks/useFetch";
import { validateResult } from "../utils/validate";

/** Add or edit one result. onSubmit({ course, semester, score }) may throw an Error to show it. */
function ResultForm({ initial, submitLabel, onSubmit, onCancel }) {
  const [values, setValues] = useState({
    course: initial?.course ?? "",
    semester: initial?.semester ?? "",
    score: initial?.score === undefined ? "" : String(initial.score),
  });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [pending, setPending] = useState(false);
  const { data: courses } = useFetch("/api/courses"); // suggestions for the course field
  const uid = useId();

  const set = (field) => (e) => setValues((v) => ({ ...v, [field]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    const found = validateResult(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setServerError("");
    setPending(true);
    try {
      await onSubmit({
        course: values.course.trim(),
        semester: values.semester.trim(),
        score: Number(values.score),
      });
    } catch (err) {
      setServerError(err.message);
      setPending(false);
    }
  }

  const field = (name, label, props = {}) => (
    <div className="field">
      <label htmlFor={`${uid}-${name}`}>{label}</label>
      <input
        id={`${uid}-${name}`}
        value={values[name]}
        onChange={set(name)}
        aria-invalid={Boolean(errors[name])}
        aria-describedby={errors[name] ? `${uid}-${name}-error` : undefined}
        {...props}
      />
      {errors[name] && (
        <p id={`${uid}-${name}-error`} className="field__error" role="alert">{errors[name]}</p>
      )}
    </div>
  );

  return (
    <form className="form form--inline" onSubmit={handleSubmit} noValidate>
      {field("course", "Course", { list: `${uid}-courses`, maxLength: 60 })}
      <datalist id={`${uid}-courses`}>
        {(courses ?? []).map((c) => <option key={c.course} value={c.course} />)}
      </datalist>
      {field("semester", "Semester", { placeholder: "e.g. 2025-1", maxLength: 20 })}
      {field("score", "Score (0-100)", { inputMode: "decimal" })}
      <div className="form__actions">
        <button type="submit" disabled={pending}>{pending ? "Saving…" : submitLabel}</button>
        <button type="button" className="button--ghost" onClick={onCancel}>Cancel</button>
      </div>
      {serverError && <p className="state state--error form__error" role="alert">{serverError}</p>}
    </form>
  );
}

export default ResultForm;
