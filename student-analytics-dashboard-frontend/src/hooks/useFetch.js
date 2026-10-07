import { useEffect, useState } from "react";
import { fetchJson } from "../api/client";

/**
 * Fetch JSON from the API. Returns { data, loading, error, refetch }.
 * Requests are aborted on unmount / path change, and `loading` is derived
 * (no synchronous setState inside the effect).
 */
export function useFetch(path) {
  const [reloadKey, setReloadKey] = useState(0);
  const requestId = `${path}#${reloadKey}`;
  const [result, setResult] = useState({ id: null, data: null, error: null });

  useEffect(() => {
    const controller = new AbortController();
    fetchJson(path, { signal: controller.signal })
      .then((data) => setResult({ id: requestId, data, error: null }))
      .catch((error) => {
        if (error.name !== "AbortError") {
          setResult({ id: requestId, data: null, error });
        }
      });
    return () => controller.abort();
  }, [path, requestId]);

  const loading = result.id !== requestId;
  return {
    data: loading ? null : result.data,
    error: loading ? null : result.error,
    loading,
    refetch: () => setReloadKey((k) => k + 1),
  };
}
