'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Server, Globe, Database, Zap, AlertTriangle } from 'lucide-react';
import { checkBackendHealth, getApiConfig, HealthCheckResult } from '@/lib/api';

interface SystemCheck {
  name: string;
  status: 'checking' | 'ok' | 'error' | 'warning';
  message: string;
  details?: string;
  icon: typeof Server;
}

export default function SmokePage() {
  const [checks, setChecks] = useState<SystemCheck[]>([
    { name: 'Frontend', status: 'ok', message: 'Next.js deployed', icon: Globe },
    { name: 'API Proxy', status: 'checking', message: 'Checking proxy route...', icon: Zap },
    { name: 'Backend', status: 'checking', message: 'Checking Railway Django...', icon: Server },
    { name: 'Database', status: 'checking', message: 'Checking PostgreSQL...', icon: Database },
  ]);
  const [healthResult, setHealthResult] = useState<HealthCheckResult | null>(null);
  const [timestamp] = useState(new Date().toISOString());
  const config = getApiConfig();

  useEffect(() => {
    const runChecks = async () => {
      const result = await checkBackendHealth();
      setHealthResult(result);

      setChecks(prev => prev.map(check => {
        if (check.name === 'API Proxy') {
          // Configuration error means proxy couldn't reach backend
          if (result.configurationError) {
            return {
              ...check,
              status: 'error',
              message: 'Configuration error',
              details: result.error,
            };
          }
          // If we got any response, proxy is working
          if (result.status > 0 || result.ok) {
            return {
              ...check,
              status: 'ok',
              message: `Proxy working (${result.latencyMs}ms)`,
            };
          }
          return {
            ...check,
            status: 'error',
            message: result.error || 'Proxy failed',
          };
        }

        if (check.name === 'Backend') {
          if (result.configurationError) {
            return {
              ...check,
              status: 'error',
              message: 'Not reachable',
              details: `Backend URL: ${result.backendUrl}`,
            };
          }
          if (result.ok) {
            return {
              ...check,
              status: 'ok',
              message: `Django OK (${result.latencyMs}ms)`,
            };
          }
          if (result.status >= 500) {
            return {
              ...check,
              status: 'error',
              message: `Server error (${result.status})`,
            };
          }
          if (result.status > 0) {
            return {
              ...check,
              status: 'warning',
              message: `Responding with ${result.status}`,
            };
          }
          return {
            ...check,
            status: 'error',
            message: result.error || 'Not reachable',
          };
        }

        if (check.name === 'Database') {
          if (result.configurationError) {
            return {
              ...check,
              status: 'error',
              message: 'Cannot verify (backend down)',
            };
          }
          if (result.ok && result.data?.database === 'ok') {
            return { ...check, status: 'ok', message: 'PostgreSQL connected' };
          }
          if (result.ok && result.data?.checks?.database === 'ok') {
            return { ...check, status: 'ok', message: 'PostgreSQL connected' };
          }
          if (result.ok && result.data?.checks?.database) {
            return {
              ...check,
              status: 'error',
              message: result.data.checks.database,
            };
          }
          if (!result.ok) {
            return {
              ...check,
              status: 'error',
              message: 'Cannot verify (backend down)',
            };
          }
          return check;
        }

        return check;
      }));
    };

    runChecks();
  }, []);

  const allOk = checks.every(c => c.status === 'ok');
  const hasErrors = checks.some(c => c.status === 'error');
  const hasWarnings = checks.some(c => c.status === 'warning');

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ok': return 'green';
      case 'error': return 'red';
      case 'warning': return 'yellow';
      default: return 'gray';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-lg w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
            allOk ? 'bg-green-100' : hasErrors ? 'bg-red-100' : hasWarnings ? 'bg-yellow-100' : 'bg-gray-100'
          }`}>
            {allOk ? (
              <CheckCircle className="h-8 w-8 text-green-600" />
            ) : hasErrors ? (
              <XCircle className="h-8 w-8 text-red-600" />
            ) : hasWarnings ? (
              <AlertTriangle className="h-8 w-8 text-yellow-600" />
            ) : (
              <Server className="h-8 w-8 text-gray-400 animate-pulse" />
            )}
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Retail Monitor</h1>
          <p className="text-gray-500 mt-1">System Health Check</p>
        </div>

        {/* Configuration Error Banner */}
        {healthResult?.configurationError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-red-800">Configuration Error</h3>
                <p className="text-sm text-red-700 mt-1">
                  The frontend cannot reach the backend. This is likely a misconfiguration.
                </p>
                <div className="mt-2 text-xs font-mono text-red-600 bg-red-100 p-2 rounded">
                  <p>Backend URL: {healthResult.backendUrl}</p>
                  <p>Error: {healthResult.error}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Checks */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden mb-6">
          {checks.map((check, index) => {
            const Icon = check.icon;
            const color = getStatusColor(check.status);
            return (
              <div
                key={check.name}
                className={`flex items-center justify-between p-4 ${
                  index !== checks.length - 1 ? 'border-b border-gray-100' : ''
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg bg-${color}-50`}>
                    <Icon className={`h-5 w-5 text-${color}-600`} />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{check.name}</p>
                    <p className="text-sm text-gray-500">{check.message}</p>
                    {check.details && (
                      <p className="text-xs text-gray-400 font-mono mt-1">{check.details}</p>
                    )}
                  </div>
                </div>
                <div>
                  {check.status === 'checking' ? (
                    <div className="h-5 w-5 rounded-full border-2 border-gray-300 border-t-gray-600 animate-spin" />
                  ) : check.status === 'ok' ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : check.status === 'warning' ? (
                    <AlertTriangle className="h-5 w-5 text-yellow-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Configuration Info */}
        <div className="bg-white rounded-xl shadow-sm p-4 text-sm mb-6">
          <h3 className="font-semibold text-gray-900 mb-3">Configuration</h3>
          <div className="space-y-2">
            <div className="flex justify-between text-gray-500">
              <span>Environment:</span>
              <span className="font-mono text-gray-700">{process.env.NODE_ENV}</span>
            </div>
            <div className="flex justify-between text-gray-500">
              <span>API Mode:</span>
              <span className="font-mono text-gray-700">{config.mode}</span>
            </div>
            <div className="flex justify-between text-gray-500">
              <span>Browser Path:</span>
              <span className="font-mono text-gray-700">{config.browserPath}</span>
            </div>
            <div className="flex justify-between text-gray-500">
              <span>Backend URL:</span>
              <span className="font-mono text-gray-700 text-xs break-all">{config.backendUrl}</span>
            </div>
            <div className="flex justify-between text-gray-500">
              <span>Timestamp:</span>
              <span className="font-mono text-gray-700 text-xs">{new Date(timestamp).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Raw Health Response */}
        {healthResult && (
          <div className="bg-white rounded-xl shadow-sm p-4 text-sm mb-6">
            <h3 className="font-semibold text-gray-900 mb-3">Raw Health Response</h3>
            <pre className={`text-xs font-mono p-3 rounded-lg overflow-x-auto ${
              healthResult.ok ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
            }`}>
              {JSON.stringify(healthResult, null, 2)}
            </pre>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-4">
          <a
            href="/"
            className="flex-1 text-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            Go to Dashboard
          </a>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Recheck
          </button>
        </div>
      </div>
    </div>
  );
}
