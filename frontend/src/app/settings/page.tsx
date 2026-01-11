'use client';

import { useState } from 'react';
import { Settings, Server, RefreshCw, CheckCircle, XCircle, Globe, Code, Zap, AlertTriangle } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/Button';
import { checkBackendHealth, getApiConfig, HealthCheckResult } from '@/lib/api';

export default function SettingsPage() {
  const [healthResult, setHealthResult] = useState<HealthCheckResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const config = getApiConfig();

  const testBackend = async () => {
    setIsTesting(true);
    setHealthResult(null);
    try {
      const result = await checkBackendHealth();
      setHealthResult(result);
    } catch (err) {
      setHealthResult({
        ok: false,
        status: 0,
        error: err instanceof Error ? err.message : 'Unknown error',
        latencyMs: 0,
        configurationError: true,
      });
    } finally {
      setIsTesting(false);
    }
  };

  // Environment info
  const commitSha = process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA?.slice(0, 7) || 'dev';
  const vercelEnv = process.env.NEXT_PUBLIC_VERCEL_ENV || 'local';

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gray-100 rounded-lg">
                <Settings className="h-6 w-6 text-gray-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
                <p className="text-gray-500">Application configuration and health</p>
              </div>
            </div>
          </div>

          <div className="grid gap-6 max-w-3xl">
            {/* Environment Info */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Globe className="h-5 w-5 text-gray-500" />
                  Environment
                </h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Vercel Environment</p>
                    <p className="font-medium text-gray-900 flex items-center gap-2">
                      <span className={`inline-block w-2 h-2 rounded-full ${
                        vercelEnv === 'production' ? 'bg-green-500' :
                        vercelEnv === 'preview' ? 'bg-yellow-500' : 'bg-gray-400'
                      }`} />
                      {vercelEnv}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Node Environment</p>
                    <p className="font-medium text-gray-900">{process.env.NODE_ENV}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Git Commit</p>
                    <p className="font-mono text-sm text-gray-900">{commitSha}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Build Time</p>
                    <p className="font-mono text-sm text-gray-900">
                      {new Date().toISOString().split('T')[0]}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* API Configuration */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Zap className="h-5 w-5 text-gray-500" />
                  API Configuration
                </h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">API Mode</p>
                    <p className="font-medium text-gray-900 capitalize">{config.mode}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Browser Path</p>
                    <p className="font-mono text-sm text-gray-900">{config.browserPath}</p>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Backend URL</p>
                  <p className="font-mono text-sm text-gray-900 break-all">{config.backendUrl}</p>
                </div>
                <div className="pt-2 border-t border-gray-100">
                  <p className="text-xs text-gray-500">
                    In production, browser requests to <code className="bg-gray-100 px-1 rounded">/api/v1/*</code> are
                    proxied by Next.js to the Railway backend. This ensures same-origin requests with no CORS issues.
                  </p>
                </div>
              </div>
            </div>

            {/* Backend Health Test */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Server className="h-5 w-5 text-gray-500" />
                  Backend Health
                </h2>
              </div>
              <div className="p-6">
                <div className="flex items-center gap-4 mb-4">
                  <Button
                    onClick={testBackend}
                    isLoading={isTesting}
                    icon={RefreshCw}
                  >
                    Test Backend Connection
                  </Button>
                  {healthResult && (
                    <span className={`flex items-center gap-1 text-sm font-medium ${
                      healthResult.ok ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {healthResult.ok ? (
                        <>
                          <CheckCircle className="h-4 w-4" />
                          Connected ({healthResult.latencyMs}ms)
                        </>
                      ) : (
                        <>
                          <XCircle className="h-4 w-4" />
                          Failed
                        </>
                      )}
                    </span>
                  )}
                </div>

                {/* Configuration Error Banner */}
                {healthResult?.configurationError && (
                  <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <h3 className="font-semibold text-red-800">Configuration Error</h3>
                        <p className="text-sm text-red-700 mt-1">
                          Cannot reach the backend. Check that NEXT_PUBLIC_API_URL is set correctly in Vercel.
                        </p>
                        <div className="mt-2 text-xs font-mono text-red-600">
                          <p>Configured URL: {healthResult.backendUrl}</p>
                          <p>Error: {healthResult.error}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {healthResult && !healthResult.configurationError && (
                  <div className={`rounded-lg p-4 ${
                    healthResult.ok ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                  }`}>
                    <pre className="text-sm font-mono overflow-x-auto">
                      {JSON.stringify(healthResult, null, 2)}
                    </pre>
                  </div>
                )}

                {!healthResult && !isTesting && (
                  <p className="text-sm text-gray-500">
                    Click the button above to test the backend connection through the same proxy path used by the application.
                  </p>
                )}
              </div>
            </div>

            {/* Quick Links */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Code className="h-5 w-5 text-gray-500" />
                  Quick Links
                </h2>
              </div>
              <div className="p-6">
                <div className="flex flex-wrap gap-3">
                  <a
                    href="/smoke/"
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
                  >
                    System Health Check
                  </a>
                  <a
                    href="/api/v1/health/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
                  >
                    Raw Health Endpoint
                  </a>
                  <a
                    href="https://github.com/Spastikinho/retail-monitor"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
                  >
                    GitHub Repository
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
