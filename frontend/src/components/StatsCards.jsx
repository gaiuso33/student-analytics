import { formatNumber } from "../utils/students";

function StatsCards({ analytics, loading, error }) {
  const show = (value, dp = 2, suffix = "") =>
    loading ? "…" : error || value === undefined || value === null ? "--" : `${formatNumber(Number(value), dp)}${suffix}`;

  const stats = [
    { label: "Total students", value: show(analytics?.total_students, 0) },
    { label: "Average GPA", value: show(analytics?.average_gpa) },
    { label: "Highest GPA", value: show(analytics?.highest_gpa) },
    { label: "Pass rate", value: show(analytics?.pass_rate, 1, "%") },
  ];

  return (
    <div className="stats-grid">
      {stats.map((s) => (
        <div className="card card--stat" key={s.label}>
          <h3>{s.label}</h3>
          <p>{s.value}</p>
        </div>
      ))}
    </div>
  );
}

export default StatsCards;
