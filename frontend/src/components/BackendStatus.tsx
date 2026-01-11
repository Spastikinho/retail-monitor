'use client';

import { useState, useEffect, useCallback } from 'react';
import { CheckCircle, XCircle, Loader2, RefreshCw, Database, Server } from 'lucide-react';
import { checkBackendHealth } from '@/lib/api';

interface BackendStatusProps {
  /** Show detailed status with individual checks */
  detailed?: boolean;
  /** Auto-refresh interval in seconds (0 to disable) */
  refreshInterval?: number;
  /** Compact mode for sidebar/header */
  compact?: boolean;
}

interface HealthState {
  status: 'checking' | 'healthy' | 'degraded' | 'error';
  message: string;
  latencyMs?: number;
  checks?: Record<string, string>;
  lastChecked: Date | null;
}

export function BackendStatus({
  detailed = false,
  refreshInterval = 0,
  compact = false,
}: BackendStatusProps) {
  const [health, setHealth] = useState<HealthState>({
    status: 'checking',
    message: 'Checking backend...',
    lastChecked: null,
  });
  const [isRefreshing, setIsRefreshing] = useState(false);

  const checkHealth = useCallback(async () => {
    setIsRefreshing(true);

    const result = await checkBackendHealth();

    if (result.ok && result.data) {
      const isHealthy = result.data.status === 'ok';
      const isDegraded = result.data.status === 'degraded';

      setHealth({
        status: isHealthy ? 'healthy' : isDegraded ? 'degraded' : 'error',
        message: isHealthy
          ? `Connected (${result.latencyMs}ms)`
          : isDegraded
          ? 'Degraded'
          : 'Unhealthy',
        latencyMs: result.latencyMs,
        checks: result.data.checks,
        lastChecked: new Date(),
      });
    } else {
      setHealth({
        status: 'error',
        message: result.error || 'Connection failed',
        latencyMs: result.latencyMs,
        lastChecked: new Date(),
      });
    }

    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    checkHealth();

    if (refreshInterval > 0) {
      const interval = setInterval(checkHealth, refreshInterval * 1000);
      return () => clearInterval(interval);
    }
  }, [checkHealth, refreshInterval]);

  const statusColors = {
    checking: 'text-gray-400',
    healthy: 'text-green-500',
    degraded: 'text-yellow-500',
    error: 'text-red-500',
  };

  const statusBgColors = {
    checking: 'bg-gray-100',
    healthy: 'bg-green-50',
    degraded: 'bg-yellow-50',
    error: 'bg-red-50',
  };

  const StatusIcon = () => {
    if (isRefreshing || health.status === 'checking') {
      return <Loader2 className="h-4 w-4 animate-spin text-gray-400" />;
    }
    if (health.status === 'healthy') {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    }
    return <XCircle className={`h-4 w-4 ${statusColors[health.status]}`} />;
  };

  if (compact) {
    return (
      <button
        onClick={checkHealth}
        disabled={isRefreshing}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${statusBgColors[health.status]}`}
        title={`Backend: ${health.message}${health.lastChecked ? ` (checked ${health.lastChecked.toLocaleTimeString()})` : ''}`}
      >
        <StatusIcon />
        <span className={statusColors[health.status]}>
          {health.status === 'healthy' ? 'API' : health.status}
        </span>
      </button>
    );
  }

  return (
    <div className={`rounded-lg border p-4 ${statusBgColors[health.status]} border-gray-200`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Server className={`h-5 w-5 ${statusColors[health.status]}`} />
          <span className="font-medium text-gray-900">Backend Status</span>
        </div>
        <button
          onClick={checkHealth}
          disabled={isRefreshing}
          className="p-1 rounded hover:bg-white/50 transition-colors disabled:opacity-50"
          title="Refresh status"
        >
          <RefreshCw className={`h-4 w-4 text-gray-500 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="flex items-center gap-2">
        <StatusIcon />
        <span className={`text-sm ${statusColors[health.status]}`}>
          {health.message}
        </span>
      </div>

      {detailed && health.checks && (
        <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
          {Object.entries(health.checks).map(([name, status]) => (
            <div key={name} className="flex items-center gap-2 text-sm">
              <Database className="h-3.5 w-3.5 text-gray-400" />
              <span className="text-gray-600 capitalize">{name}:</span>
              <span className={status === 'ok' ? 'text-green-600' : 'text-red-600'}>
                {status}
              </span>
            </div>
          ))}
        </div>
      )}

      {health.lastChecked && (
        <p className="mt-2 text-xs text-gray-400">
          Last checked: {health.lastChecked.toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}
