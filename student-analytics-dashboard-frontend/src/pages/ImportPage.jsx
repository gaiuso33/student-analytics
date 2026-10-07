import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { request } from "../api/client";
import { downloadCsv } from "../utils/csv";

const MAX_BYTES = 2 * 1024 * 1024;
const TEMPLATE = "Student,Course,Semester,Score\r\nAda Eze,Mathematics,2025-1,78\r\nAda Eze,English,2025-1,85\r\n";

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

function ImportPage() {
  const [fileName, setFileName] = useState("");
  const [text, setText] = useState("");
  const [mode, setMode] = useState("skip");
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(null);
  const latest = useRef(0); // ignore answers to superseded requests

  async function runPreview(csvText, duplicateMode) {
    const ticket = ++latest.current;
    setPending(true);
    setError("");
    setPreview(null);
    try {
      const data = await request("/api/import", {
        method: "POST",
        body: { csv: csvText, dry_run: true, on_duplicate: duplicateMode },
      });
      if (ticket === latest.current) setPreview(data);
    } catch (err) {
      if (ticket === latest.current) setError(err.message);
    } finally {
      if (ticket === latest.current) setPending(false);
    }
  }

  async function handleFile(e) {
    const file = e.target.files?.[0];
    setDone(null);
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setError("That file is larger than 2 MB. Split it into smaller files.");
      setPreview(null);
      setText("");
      setFileName(file.name);
      return;
    }
    const content = await file.text();
    setFileName(file.name);
    setText(content);
    runPreview(content, mode);
  }

  function handleMode(e) {
    setMode(e.target.value);
    if (text) runPreview(text, e.target.value);
  }

  async function handleImport() {
    setPending(true);
    setError("");
    try {
      const data = await request("/api/import", {
        method: "POST",
        body: { csv: text, dry_run: false, on_duplicate: mode },
      });
      setDone(data);
      setPreview(null);
      setText("");
      setFileName("");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  const canImport = preview && preview.error_count === 0 && !pending;
  const changes = preview ? preview.records_created + preview.records_updated : 0;

  return (
    <div className="page">
      <header className="page-header">
        <h1>Import results from CSV</h1>
        <Link to="/students">Back to students</Link>
      </header>

      <section className="card form-card">
        <p>
          Upload a CSV with the columns <strong>Student, Course, Semester, Score</strong>. Existing students are matched
          by name (ignoring capital letters) and new ones are created. Nothing is saved until you confirm, and if any
          row has a problem, nothing is imported at all.
        </p>
        <p>
          <button type="button" className="button--ghost button--small"
            onClick={() => downloadCsv("student-import-template.csv", TEMPLATE)}>
            Download template
          </button>
        </p>

        <div className="form">
          <div className="field">
            <label htmlFor="import-file">CSV file</label>
            <input id="import-file" type="file" accept=".csv,text/csv" onChange={handleFile} />
          </div>

          <fieldset className="radio-group">
            <legend>If a result already exists for that student, course and semester</legend>
            <label>
              <input type="radio" name="dup" value="skip" checked={mode === "skip"} onChange={handleMode} />
              Keep the existing score
            </label>
            <label>
              <input type="radio" name="dup" value="update" checked={mode === "update"} onChange={handleMode} />
              Replace it with the score in the file
            </label>
          </fieldset>
        </div>
      </section>

      {pending && !preview && <p className="state" role="status">Checking {fileName || "file"}…</p>}
      {error && <p className="state state--error" role="alert">{error}</p>}

      {done && (
        <p className="notice" role="status">
          Import complete: {plural(done.students_created, "new student")}, {plural(done.records_created, "result")} added,{" "}
          {done.records_updated} updated, {done.records_skipped} skipped.{" "}
          <Link to="/students">View students</Link>
        </p>
      )}

      {preview && (
        <section className="card form-card" aria-live="polite">
          <h2>Preview: {fileName}</h2>
          <ul className="summary-list">
            <li>{plural(preview.total_rows, "row")} read</li>
            <li>{plural(preview.students_created, "new student")} to create</li>
            <li>{plural(preview.records_created, "result")} to add</li>
            <li>{preview.records_updated} to update, {preview.records_skipped} already there and skipped</li>
          </ul>

          {preview.error_count > 0 ? (
            <>
              <p className="state state--error" role="alert">
                {plural(preview.error_count, "row")} can't be imported. Fix the file and choose it again.
              </p>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Row</th><th>Problem</th></tr></thead>
                  <tbody>
                    {preview.errors.map((e) => (
                      <tr key={`${e.row}-${e.message}`}><td>{e.row}</td><td>{e.message}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {preview.error_count > preview.errors.length && (
                <p className="muted">Showing the first {preview.errors.length} problems.</p>
              )}
            </>
          ) : (
            <div className="form__actions form__actions--flush">
              <button type="button" onClick={handleImport} disabled={!canImport || changes + preview.students_created === 0}>
                {pending ? "Importing…" : `Import ${plural(changes, "result")}`}
              </button>
              {changes + preview.students_created === 0 && (
                <span className="muted">Nothing new to import.</span>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default ImportPage;
