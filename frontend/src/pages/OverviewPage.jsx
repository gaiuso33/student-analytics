import { Link } from "react-router-dom";
import Charts from "../components/Charts";
import StatsCards from "../components/StatsCards";
import InsightsCard from "../components/InsightsCard";
import Leaderboard from "../components/Leaderboard";
import CourseDifficulty from "../components/CourseDifficulty";
import AtRiskStudents from "../components/AtRiskStudents";
import { useFetch } from "../hooks/useFetch";

function OverviewPage() {
  const students = useFetch("/api/students");
  const analytics = useFetch("/api/analytics");

  return (
    <div className="page">
      <header className="page-header">
        <h1>Overview</h1>
        <Link to="/students">View all student records</Link>
      </header>

      <StatsCards analytics={analytics.data} loading={analytics.loading} error={analytics.error} />

      <InsightsCard />

      <div className="dashboard-grid">
        <Leaderboard />
        <CourseDifficulty />
        <AtRiskStudents />
      </div>

      {students.loading && <p className="state">Loading charts…</p>}
      {students.error && (
        <div className="state state--error" role="alert">
          <p>{students.error.message}</p>
          <button type="button" onClick={students.refetch}>Try again</button>
        </div>
      )}
      {students.data && <Charts students={students.data} />}
    </div>
  );
}

export default OverviewPage;
