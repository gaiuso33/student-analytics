import { Routes, Route } from "react-router-dom";
import RequireAuth from "./auth/RequireAuth";
import RequireAdmin from "./auth/RequireAdmin";
import LoginPage from "./pages/LoginPage";
import OverviewPage from "./pages/OverviewPage";
import StudentsPage from "./pages/StudentsPage";
import StudentDetailPage from "./pages/StudentDetailPage";
import NewStudentPage from "./pages/NewStudentPage";
import CoursesPage from "./pages/CoursesPage";
import FollowUpsPage from "./pages/FollowUpsPage";
import AccountPage from "./pages/AccountPage";
import UsersPage from "./pages/UsersPage";
import AuditPage from "./pages/AuditPage";
import ImportPage from "./pages/ImportPage";
import NotFoundPage from "./pages/NotFoundPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/students" element={<StudentsPage />} />
        <Route path="/students/:id" element={<StudentDetailPage />} />
        <Route path="/courses" element={<CoursesPage />} />
        <Route path="/interventions" element={<FollowUpsPage />} />
        <Route path="/account" element={<AccountPage />} />

        <Route element={<RequireAdmin />}>
          <Route path="/students/new" element={<NewStudentPage />} />
          <Route path="/admin/users" element={<UsersPage />} />
          <Route path="/admin/import" element={<ImportPage />} />
          <Route path="/admin/audit" element={<AuditPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export default App;
