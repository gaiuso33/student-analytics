import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import OverviewPage from "./pages/OverviewPage";
import StudentsPage from "./pages/StudentsPage";
import StudentDetailPage from "./pages/StudentDetailPage";
import CoursesPage from "./pages/CoursesPage";
import NotFoundPage from "./pages/NotFoundPage";

function App() {
  return (
    <div className="layout">
      <Sidebar />
      <main className="main">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/students" element={<StudentsPage />} />
          <Route path="/students/:id" element={<StudentDetailPage />} />
          <Route path="/courses" element={<CoursesPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
