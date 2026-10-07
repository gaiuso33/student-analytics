import { Link } from "react-router-dom";

function NotFoundPage() {
  return (
    <div className="page">
      <h1>Page not found</h1>
      <p>That address doesn't match any page. <Link to="/">Go to the overview</Link>.</p>
    </div>
  );
}

export default NotFoundPage;
