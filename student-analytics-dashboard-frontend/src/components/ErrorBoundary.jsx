import { Component } from "react";

/** Stops one crashing component from blanking the whole app. */
class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled UI error:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="page" role="alert">
        <h1>Something went wrong</h1>
        <p className="state state--error">The page hit an unexpected error. Reloading usually fixes it.</p>
        <button type="button" onClick={() => window.location.reload()}>Reload page</button>
      </div>
    );
  }
}

export default ErrorBoundary;
