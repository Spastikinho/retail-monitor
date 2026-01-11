'use client';

import { AlertTriangle, RefreshCw, ExternalLink, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { ApiError } from '@/lib/api';

export interface ApiErrorInfo {
  operation: string;        // What were we trying to do? e.g., "Loading dashboard data"
  endpoint?: string;        // API endpoint that failed e.g., "/api/v1/analytics/summary/"
  status?: number;          // HTTP status code
  message: string;          // Error message
  details?: Record<string, unknown> | string | null;  // Additional error details
  timestamp?: string;       // When did this happen
}

interface ApiErrorCardProps {
  error: ApiErrorInfo;
  onRetry?: () => void;
  isRetrying?: boolean;
  compact?: boolean;
}

/**
 * Structured error card that displays diagnostic information for API failures.
 * Helps users and developers understand what went wrong.
 */
export function ApiErrorCard({ error, onRetry, isRetrying, compact = false }: ApiErrorCardProps) {
  const [copied, setCopied] = useState(false);

  const getStatusDescription = (status?: number): string => {
    if (!status) return 'Connection failed';
    if (status === 0) return 'Network error (no response)';
    if (status === 401) return 'Authentication required';
    if (status === 403) return 'Access denied';
    if (status === 404) return 'Resource not found';
    if (status === 408) return 'Request timeout';
    if (status === 429) return 'Too many requests';
    if (status === 500) return 'Server error';
    if (status === 502) return 'Backend unreachable';
    if (status === 503) return 'Service unavailable';
    if (status >= 400 && status < 500) return 'Client error';
    if (status >= 500) return 'Server error';
    return `HTTP ${status}`;
  };

  const getHelpHint = (status?: number, endpoint?: string): string => {
    if (!status || status === 0) {
      return 'Check your internet connection and try again. If the problem persists, the backend may be down.';
    }
    if (status === 401) {
      return 'Please log in to access this feature.';
    }
    if (status === 403) {
      return 'You do not have permission to access this resource.';
    }
    if (status === 404) {
      return 'The requested resource does not exist or has been moved.';
    }
    if (status === 502 || status === 503) {
      return 'The backend server is not responding. Check /smoke for system status.';
    }
    if (status >= 500) {
      return 'A server error occurred. Please try again or contact support.';
    }
    return 'An unexpected error occurred. Please try again.';
  };

  const copyDiagnostics = () => {
    const diagnostics = {
      operation: error.operation,
      endpoint: error.endpoint,
      status: error.status,
      statusDescription: getStatusDescription(error.status),
      message: error.message,
      details: error.details,
      timestamp: error.timestamp || new Date().toISOString(),
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
    };
    navigator.clipboard.writeText(JSON.stringify(diagnostics, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (compact) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-red-800">{error.operation} failed</p>
            <p className="text-sm text-red-600 mt-1">{error.message}</p>
            {error.status && (
              <p className="text-xs text-red-500 mt-1">
                {error.endpoint && <span className="font-mono">{error.endpoint}</span>}
                {error.endpoint && ' • '}
                {getStatusDescription(error.status)}
              </p>
            )}
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              disabled={isRetrying}
              className="flex-shrink-0 p-2 text-red-600 hover:bg-red-100 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${isRetrying ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-red-50 border border-red-200 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-red-100 border-b border-red-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-red-600" />
          <span className="font-semibold text-red-800">{error.operation} failed</span>
        </div>
        {error.status && (
          <span className="px-2 py-1 bg-red-200 text-red-800 text-xs font-mono rounded">
            {error.status} {getStatusDescription(error.status)}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Error Message */}
        <div>
          <p className="text-red-800">{error.message}</p>
        </div>

        {/* Technical Details */}
        {(error.endpoint || error.details) && (
          <div className="space-y-2">
            {error.endpoint && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-red-600">Endpoint:</span>
                <code className="px-2 py-0.5 bg-red-100 rounded text-red-800 font-mono text-xs">
                  {error.endpoint}
                </code>
              </div>
            )}
            {error.details && typeof error.details === 'object' && (
              <details className="text-sm">
                <summary className="cursor-pointer text-red-600 hover:text-red-700">
                  Show technical details
                </summary>
                <pre className="mt-2 p-2 bg-red-100 rounded text-xs text-red-800 overflow-x-auto">
                  {JSON.stringify(error.details, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}

        {/* Help Hint */}
        <div className="p-3 bg-white/50 rounded-lg border border-red-200">
          <p className="text-sm text-red-700">
            <strong>Hint:</strong> {getHelpHint(error.status, error.endpoint)}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          {onRetry && (
            <button
              onClick={onRetry}
              disabled={isRetrying}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${isRetrying ? 'animate-spin' : ''}`} />
              {isRetrying ? 'Retrying...' : 'Try again'}
            </button>
          )}
          <button
            onClick={copyDiagnostics}
            className="inline-flex items-center gap-2 px-4 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-100 transition-colors"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied!' : 'Copy diagnostics'}
          </button>
          <a
            href="/smoke/"
            className="inline-flex items-center gap-2 px-4 py-2 text-red-600 hover:text-red-700 transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
            Check system status
          </a>
        </div>
      </div>
    </div>
  );
}

/**
 * Helper function to create ApiErrorInfo from various error types
 */
export function createApiErrorInfo(
  operation: string,
  error: unknown,
  endpoint?: string
): ApiErrorInfo {
  if (error instanceof ApiError) {
    return {
      operation,
      endpoint: endpoint,
      status: error.status,
      message: error.message,
      details: error.details,
      timestamp: new Date().toISOString(),
    };
  }

  if (error instanceof Error) {
    // Try to extract status from error message patterns
    const statusMatch = error.message.match(/(\d{3})/);
    return {
      operation,
      endpoint,
      status: statusMatch ? parseInt(statusMatch[1]) : 0,
      message: error.message,
      timestamp: new Date().toISOString(),
    };
  }

  return {
    operation,
    endpoint,
    status: 0,
    message: String(error) || 'An unknown error occurred',
    timestamp: new Date().toISOString(),
  };
}

/**
 * Log API error with structured data (console in dev, can be extended for Sentry)
 */
export function logApiError(errorInfo: ApiErrorInfo): void {
  const logData = {
    type: 'api_error',
    ...errorInfo,
    environment: process.env.NODE_ENV,
    url: typeof window !== 'undefined' ? window.location.href : 'unknown',
  };

  // Always log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.error('[API Error]', logData);
  } else {
    // In production, log structured data
    console.error(JSON.stringify(logData));
  }

  // TODO: Add Sentry integration here if SENTRY_DSN is configured
  // if (typeof window !== 'undefined' && window.Sentry) {
  //   window.Sentry.captureException(new Error(errorInfo.message), {
  //     extra: logData,
  //   });
  // }
}
