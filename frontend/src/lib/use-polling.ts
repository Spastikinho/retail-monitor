/**
 * Polling Hook with Exponential Backoff
 * Phase 5 Implementation - Smart polling for run status
 */

import { useEffect, useRef, useCallback, useState } from 'react';

export interface PollingOptions<T> {
  /** Function to fetch data */
  fetcher: () => Promise<T>;
  /** Condition to stop polling */
  stopCondition: (data: T) => boolean;
  /** Initial interval in ms (default: 1000) */
  initialInterval?: number;
  /** Maximum interval in ms (default: 10000) */
  maxInterval?: number;
  /** Backoff multiplier (default: 1.5) */
  backoffMultiplier?: number;
  /** Maximum number of retries on error (default: 3) */
  maxRetries?: number;
  /** Callback on successful fetch */
  onSuccess?: (data: T) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
  /** Callback when polling stops */
  onStop?: (reason: 'condition' | 'error' | 'manual') => void;
  /** Whether to start polling immediately (default: true) */
  enabled?: boolean;
}

export interface PollingState<T> {
  data: T | null;
  error: Error | null;
  isPolling: boolean;
  pollCount: number;
  currentInterval: number;
}

export interface PollingResult<T> extends PollingState<T> {
  start: () => void;
  stop: () => void;
  reset: () => void;
}

export function usePolling<T>(options: PollingOptions<T>): PollingResult<T> {
  const {
    fetcher,
    stopCondition,
    initialInterval = 1000,
    maxInterval = 10000,
    backoffMultiplier = 1.5,
    maxRetries = 3,
    onSuccess,
    onError,
    onStop,
    enabled = true,
  } = options;

  const [state, setState] = useState<PollingState<T>>({
    data: null,
    error: null,
    isPolling: false,
    pollCount: 0,
    currentInterval: initialInterval,
  });

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);
  const isMountedRef = useRef(true);
  const isPollingRef = useRef(false);

  const clearTimeoutSafe = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const stop = useCallback((reason: 'condition' | 'error' | 'manual' = 'manual') => {
    clearTimeoutSafe();
    isPollingRef.current = false;
    if (isMountedRef.current) {
      setState(prev => ({ ...prev, isPolling: false }));
      onStop?.(reason);
    }
  }, [clearTimeoutSafe, onStop]);

  const poll = useCallback(async (interval: number) => {
    if (!isPollingRef.current || !isMountedRef.current) return;

    try {
      const data = await fetcher();

      if (!isMountedRef.current) return;

      retryCountRef.current = 0; // Reset retries on success

      setState(prev => ({
        ...prev,
        data,
        error: null,
        pollCount: prev.pollCount + 1,
      }));

      onSuccess?.(data);

      // Check stop condition
      if (stopCondition(data)) {
        stop('condition');
        return;
      }

      // Calculate next interval with backoff
      const nextInterval = Math.min(interval * backoffMultiplier, maxInterval);

      if (isMountedRef.current) {
        setState(prev => ({ ...prev, currentInterval: nextInterval }));
      }

      // Schedule next poll
      if (isPollingRef.current) {
        timeoutRef.current = setTimeout(() => poll(nextInterval), nextInterval);
      }
    } catch (error) {
      if (!isMountedRef.current) return;

      const err = error instanceof Error ? error : new Error(String(error));

      retryCountRef.current++;

      setState(prev => ({ ...prev, error: err }));
      onError?.(err);

      // Check if we should stop due to too many errors
      if (retryCountRef.current >= maxRetries) {
        stop('error');
        return;
      }

      // Retry with increased interval
      const nextInterval = Math.min(interval * backoffMultiplier, maxInterval);

      if (isPollingRef.current) {
        timeoutRef.current = setTimeout(() => poll(nextInterval), nextInterval);
      }
    }
  }, [fetcher, stopCondition, backoffMultiplier, maxInterval, maxRetries, onSuccess, onError, stop]);

  const start = useCallback(() => {
    if (isPollingRef.current) return;

    isPollingRef.current = true;
    retryCountRef.current = 0;

    setState(prev => ({
      ...prev,
      isPolling: true,
      pollCount: 0,
      currentInterval: initialInterval,
      error: null,
    }));

    // Start polling immediately
    poll(initialInterval);
  }, [initialInterval, poll]);

  const reset = useCallback(() => {
    stop('manual');
    setState({
      data: null,
      error: null,
      isPolling: false,
      pollCount: 0,
      currentInterval: initialInterval,
    });
    retryCountRef.current = 0;
  }, [stop, initialInterval]);

  // Auto-start if enabled
  useEffect(() => {
    if (enabled) {
      start();
    }
    return () => {
      stop('manual');
    };
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      clearTimeoutSafe();
    };
  }, [clearTimeoutSafe]);

  return {
    ...state,
    start,
    stop: () => stop('manual'),
    reset,
  };
}

/**
 * Simple hook for one-time fetch with retry
 */
export function useFetchWithRetry<T>(
  fetcher: () => Promise<T>,
  options: { maxRetries?: number; retryDelay?: number; enabled?: boolean } = {}
) {
  const { maxRetries = 3, retryDelay = 1000, enabled = true } = options;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const result = await fetcher();
        setData(result);
        setIsLoading(false);
        return result;
      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err));

        if (attempt < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, retryDelay * (attempt + 1)));
        }
      }
    }

    setError(lastError);
    setIsLoading(false);
    throw lastError;
  }, [fetcher, maxRetries, retryDelay]);

  useEffect(() => {
    if (enabled) {
      fetch();
    }
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, error, isLoading, refetch: fetch };
}
