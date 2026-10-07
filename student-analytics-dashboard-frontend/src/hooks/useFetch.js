import { useEffect, useState } from "react";
import { fetchJson } from "../api/client";

/**
 * Fetch JSON from the API. Returns { data, loading, error, refetch }.
 * - Requests are aborted on unmount / path change.
 * - `loading` is derived (no synchronous setState inside the effect).
 * - When refetching the same path, the previous data stays on screen instead of flashing a spinner.
 */
export function useFetch(path) {
  const [reloadKey, setReloadKey] = useState(0);
  const requestId = `${path}#${reloadKey}`;
  const [result, setResult] = useState({ id: null, path: null, data: null, error: null });

  useEffect(() => {
    const controller = new AbortController();
    fetchJson(path, { signal: controller.signal })
      .then((data) => setResult({ id: requestId, path, data, error: null }))
      .catch((error) => {
        if (error.name !== "AbortError") {
          setResult({ id: requestId, path, data: null, error });
        }
      });
    return () => controller.abort();
  }, [path, requestId]);

  const pending = result.id !== requestId;
  const keepOldData = pending && result.path === path && result.data !== null;
  return {
    data: pending && !keepOldData ? null : result.data,
    error: pending ? null : result.error,
    loading: pending && !keepOldData,
    refetch: () => setReloadKey((k) => k + 1),
  };
}
