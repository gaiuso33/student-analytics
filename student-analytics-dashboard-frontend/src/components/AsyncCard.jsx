/** Card that shows a loading, error, or content state. */
function AsyncCard({ title, loading, error, onRetry, className = "", children }) {
  return (
    <section className={`card ${className}`.trim()} aria-busy={loading}>
      <h2>{title}</h2>
      {loading && <p className="state">Loading…</p>}
      {!loading && error && (
        <div className="state state--error" role="alert">
          <p>{error.message}</p>
          {onRetry && <button type="button" onClick={onRetry}>Try again</button>}
        </div>
      )}
      {!loading && !error && children}
    </section>
  );
}

export default AsyncCard;
