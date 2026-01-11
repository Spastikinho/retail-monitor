'use client';

import { useState } from 'react';
import { Settings, Server, RefreshCw, CheckCircle, XCircle, Globe, Code, Zap } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/Button';
import { checkBackendHealth } from '@/lib/api';

interface HealthResult {
  ok: boolean;
  status: number;
  data?: { status: string; checks?: Record<string, string> };
  error?: string;
  latencyMs: number;
}

export default function SettingsPage() {
  const [healthResult, setHealthResult] = useState<HealthResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);

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
      });
    } finally {
      setIsTesting(false);
    }
  };

  // Environment info
  const environment = process.env.NODE_ENV;
  const isProduction = environment === 'production';
  const apiMode = isProduction ? 'Proxy via /api/v1/* → Railway' : 'Direct to NEXT_PUBLIC_API_URL';
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
                    <p className="text-sm text-gray-500">Environment</p>
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
                    <p className="font-medium text-gray-900">{environment}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Commit</p>
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
                <div>
                  <p className="text-sm text-gray-500">API Mode</p>
                  <p className="font-medium text-gray-900">{apiMode}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Backend URL</p>
                  <p className="font-mono text-sm text-gray-900 break-all">
                    {process.env.NEXT_PUBLIC_API_URL || 'https://web-production-9f63.up.railway.app'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Proxy Route</p>
                  <p className="font-mono text-sm text-gray-900">/api/v1/* → Railway backend</p>
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

                {healthResult && (
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
                    Click the button above to test the backend connection through the same path used by the application.
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
                    href="/smoke"
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
