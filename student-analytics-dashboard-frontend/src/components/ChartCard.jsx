import { ResponsiveContainer } from "recharts";

function ChartCard({ title, empty, children }) {
  return (
    <section className="chart-card">
      <h2>{title}</h2>
      {empty ? (
        <p className="state">Not enough data to draw this chart.</p>
      ) : (
        <div className="chart-card__plot">
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}

export default ChartCard;
