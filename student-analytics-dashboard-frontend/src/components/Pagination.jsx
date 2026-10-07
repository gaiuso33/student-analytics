function Pagination({ page, pageCount, total, start, size, sizes, onPage, onSize }) {
  if (total === 0) return null;
  const from = start + 1;
  const to = Math.min(start + size, total);

  return (
    <nav className="pagination" aria-label="Pagination">
      <span className="muted">{from}–{to} of {total}</span>
      <div className="pagination__controls">
        <button type="button" className="button--ghost" onClick={() => onPage(page - 1)} disabled={page <= 1}>
          Previous
        </button>
        <span aria-current="page">Page {page} of {pageCount}</span>
        <button type="button" className="button--ghost" onClick={() => onPage(page + 1)} disabled={page >= pageCount}>
          Next
        </button>
      </div>
      <label className="pagination__size">
        Rows per page
        <select value={size} onChange={(e) => onSize(Number(e.target.value))}>
          {sizes.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
    </nav>
  );
}

export default Pagination;
