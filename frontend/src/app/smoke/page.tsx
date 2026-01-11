'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Clock, Server } from 'lucide-react';

interface HealthStatus {
  frontend: 'ok' | 'error';
  backend: 'ok' | 'error' | 'pending';
  backendMessage?: string;
  timestamp: string;
}

export default function SmokePage() {
  const [status, setStatus] = useState<HealthStatus>({
    frontend: 'ok',
    backend: 'pending',
    timestamp: new Date().toISOString(),
  });

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch('/api/v1/health/', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        if (response.ok) {
          const data = await response.json();
          setStatus(prev => ({
            ...prev,
            backend: 'ok',
            backendMessage: `DB: ${data.database || 'connected'}`,
            timestamp: new Date().toISOString(),
          }));
        } else {
          setStatus(prev => ({
            ...prev,
            backend: 'error',
            backendMessage: `HTTP ${response.status}`,
            timestamp: new Date().toISOString(),
          }));
        }
      } catch (error) {
        setStatus(prev => ({
          ...prev,
          backend: 'error',
          backendMessage: error instanceof Error ? error.message : 'Connection failed',
          timestamp: new Date().toISOString(),
        }));
      }
    };

    checkBackend();
  }, []);

  const getIcon = (state: 'ok' | 'error' | 'pending') => {
    switch (state) {
      case 'ok':
        return <CheckCircle className="h-6 w-6 text-green-500" />;
      case 'error':
        return <XCircle className="h-6 w-6 text-red-500" />;
      case 'pending':
        return <Clock className="h-6 w-6 text-yellow-500 animate-pulse" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
            <Server className="h-8 w-8 text-primary-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Retail Monitor</h1>
          <p className="text-gray-500 mt-1">Deployment Smoke Test</p>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center">
              {getIcon(status.frontend)}
              <span className="ml-3 font-medium text-gray-900">Frontend (Vercel)</span>
            </div>
            <span className="text-sm text-gray-500">
              {status.frontend === 'ok' ? 'Deployed' : 'Error'}
            </span>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center">
              {getIcon(status.backend)}
              <span className="ml-3 font-medium text-gray-900">Backend (Railway)</span>
            </div>
            <span className="text-sm text-gray-500">
              {status.backend === 'pending' ? 'Checking...' : status.backendMessage || status.backend}
            </span>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">Last checked:</span>
            <span className="text-gray-700 font-mono">
              {new Date(status.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-gray-500">Environment:</span>
            <span className="text-gray-700 font-mono">
              {process.env.NODE_ENV}
            </span>
          </div>
        </div>

        <div className="mt-6">
          <a
            href="/"
            className="block w-full text-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            Go to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
