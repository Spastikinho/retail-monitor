'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Server, Globe, Database, Zap } from 'lucide-react';
import { BackendStatus } from '@/components/BackendStatus';
import { checkBackendHealth } from '@/lib/api';

interface SystemCheck {
  name: string;
  status: 'checking' | 'ok' | 'error';
  message: string;
  icon: typeof Server;
}

export default function SmokePage() {
  const [checks, setChecks] = useState<SystemCheck[]>([
    { name: 'Frontend', status: 'ok', message: 'Next.js running on Vercel', icon: Globe },
    { name: 'API Proxy', status: 'checking', message: 'Checking Vercel rewrites...', icon: Zap },
    { name: 'Backend', status: 'checking', message: 'Checking Railway Django...', icon: Server },
    { name: 'Database', status: 'checking', message: 'Checking PostgreSQL...', icon: Database },
  ]);
  const [timestamp] = useState(new Date().toISOString());

  useEffect(() => {
    const runChecks = async () => {
      // Check backend health (this tests proxy + backend + database)
      const result = await checkBackendHealth();

      setChecks(prev => prev.map(check => {
        if (check.name === 'API Proxy') {
          // If we got any response, proxy is working
          if (result.status > 0 || result.ok) {
            return { ...check, status: 'ok', message: `Proxy working (${result.latencyMs}ms)` };
          }
          return { ...check, status: 'error', message: result.error || 'Proxy failed' };
        }

        if (check.name === 'Backend') {
          if (result.ok) {
            return { ...check, status: 'ok', message: `Django OK (${result.latencyMs}ms)` };
          }
          if (result.status >= 500) {
            return { ...check, status: 'error', message: `Server error (${result.status})` };
          }
          if (result.status > 0) {
            return { ...check, status: 'ok', message: `Responding (${result.status})` };
          }
          return { ...check, status: 'error', message: result.error || 'Not reachable' };
        }

        if (check.name === 'Database') {
          if (result.ok && result.data?.checks?.database === 'ok') {
            return { ...check, status: 'ok', message: 'PostgreSQL connected' };
          }
          if (result.ok && result.data?.checks?.database) {
            return { ...check, status: 'error', message: result.data.checks.database };
          }
          if (!result.ok) {
            return { ...check, status: 'error', message: 'Cannot verify (backend down)' };
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

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-lg w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
            allOk ? 'bg-green-100' : hasErrors ? 'bg-red-100' : 'bg-yellow-100'
          }`}>
            {allOk ? (
              <CheckCircle className="h-8 w-8 text-green-600" />
            ) : hasErrors ? (
              <XCircle className="h-8 w-8 text-red-600" />
            ) : (
              <Server className="h-8 w-8 text-yellow-600 animate-pulse" />
            )}
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Retail Monitor</h1>
          <p className="text-gray-500 mt-1">System Health Check</p>
        </div>

        {/* Checks */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden mb-6">
          {checks.map((check, index) => {
            const Icon = check.icon;
            return (
              <div
                key={check.name}
                className={`flex items-center justify-between p-4 ${
                  index !== checks.length - 1 ? 'border-b border-gray-100' : ''
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    check.status === 'ok' ? 'bg-green-50' :
                    check.status === 'error' ? 'bg-red-50' : 'bg-gray-50'
                  }`}>
                    <Icon className={`h-5 w-5 ${
                      check.status === 'ok' ? 'text-green-600' :
                      check.status === 'error' ? 'text-red-600' : 'text-gray-400'
                    }`} />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{check.name}</p>
                    <p className="text-sm text-gray-500">{check.message}</p>
                  </div>
                </div>
                <div>
                  {check.status === 'checking' ? (
                    <div className="h-5 w-5 rounded-full border-2 border-gray-300 border-t-gray-600 animate-spin" />
                  ) : check.status === 'ok' ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Detailed Backend Status */}
        <div className="mb-6">
          <BackendStatus detailed refreshInterval={30} />
        </div>

        {/* Info */}
        <div className="bg-white rounded-xl shadow-sm p-4 text-sm">
          <div className="flex justify-between text-gray-500 mb-2">
            <span>Environment:</span>
            <span className="font-mono text-gray-700">{process.env.NODE_ENV}</span>
          </div>
          <div className="flex justify-between text-gray-500 mb-2">
            <span>Timestamp:</span>
            <span className="font-mono text-gray-700">{new Date(timestamp).toLocaleString()}</span>
          </div>
          <div className="flex justify-between text-gray-500">
            <span>API Route:</span>
            <span className="font-mono text-gray-700">/api/v1/* → Railway</span>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex gap-4">
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
