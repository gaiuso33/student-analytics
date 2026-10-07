import { Link, useNavigate } from "react-router-dom";
import NameForm from "../components/NameForm";
import { request } from "../api/client";

function NewStudentPage() {
  const navigate = useNavigate();

  async function create(name) {
    const student = await request("/api/students", { method: "POST", body: { name } });
    navigate(`/students/${student.id}`); // then add their results on the next page
  }

  return (
    <div className="page">
      <p><Link to="/students">Back to students</Link></p>
      <header className="page-header">
        <h1>Add student</h1>
      </header>
      <section className="card form-card">
        <p className="state">You'll add their course results on the next page. A student appears in the records table once they have a result.</p>
        <NameForm submitLabel="Create student" onSubmit={create} onCancel={() => navigate("/students")} />
      </section>
    </div>
  );
}

export default NewStudentPage;
