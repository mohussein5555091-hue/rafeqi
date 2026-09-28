import { useCallback, useEffect, useRef, useState } from 'react';

export interface Query<T> {
  data: T | undefined;
  loading: boolean;
  error: Error | undefined;
  reload: () => void;
  setData: (d: T) => void;
}

/** Minimal async hook. Swap for TanStack Query later without touching screens' JSX. */
export function useQuery<T>(fn: () => Promise<T>, deps: unknown[] = []): Query<T> {
  const [data, setData] = useState<T>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error>();
  const [tick, setTick] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(undefined);
    fnRef.current()
      .then((d) => alive && setData(d))
      .catch((e: Error) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, ...deps]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, reload, setData };
}
