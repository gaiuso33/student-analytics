import AsyncCard from "../components/AsyncCard";
import { useFetch } from "../hooks/useFetch";

function AuditPage() {
  const { data, loading, error, refetch } = useFetch("/api/audit?limit=200");
  const entries = data ?? [];

  return (
    <div className="page">
      <header className="page-header">
        <h1>Audit log</h1>
        <button type="button" className="button--ghost" onClick={refetch}>Refresh</button>
      </header>

      <AsyncCard title="Latest 200 events" loading={loading} error={error} onRetry={refetch}>
        {entries.length === 0 ? (
          <p className="state">Nothing recorded yet.</p>
        ) : (
          <div className="table-wrap table-wrap--flat">
            <table>
              <thead>
                <tr><th>Time (UTC)</th><th>User</th><th>Action</th><th>Details</th></tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td>{e.ts}</td>
                    <td>{e.username ?? "-"}</td>
                    <td>{e.action}</td>
                    <td>{e.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AsyncCard>
    </div>
  );
}

export default AuditPage;
