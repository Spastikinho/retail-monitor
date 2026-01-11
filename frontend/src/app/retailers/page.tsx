'use client';

import { useEffect, useState } from 'react';
import { Store, ExternalLink, RefreshCw } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { DataTable } from '@/components/DataTable';
import { Button } from '@/components/Button';
import { ApiErrorCard, createApiErrorInfo, logApiError, ApiErrorInfo } from '@/components/ApiErrorCard';
import { api, Retailer } from '@/lib/api';

export default function RetailersPage() {
  const [retailers, setRetailers] = useState<Retailer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiErrorInfo | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const fetchRetailers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getRetailers();
      setRetailers(res.retailers);
    } catch (err) {
      const errorInfo = createApiErrorInfo('Loading retailers', err, '/api/v1/retailers/');
      logApiError(errorInfo);
      setError(errorInfo);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    await fetchRetailers();
    setIsRetrying(false);
  };

  useEffect(() => {
    fetchRetailers();
  }, []);

  const columns = [
    {
      key: 'name',
      header: 'Retailer',
      render: (retailer: Retailer) => (
        <div className="flex items-center">
          <Store className="mr-3 h-5 w-5 text-gray-400" />
          <div>
            <p className="font-medium text-gray-900">{retailer.name}</p>
            <p className="text-sm text-gray-500">{retailer.code}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'website',
      header: 'Website',
      render: (retailer: Retailer) =>
        retailer.website ? (
          <a
            href={retailer.website}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center text-primary-600 hover:text-primary-700"
          >
            {retailer.website}
            <ExternalLink className="ml-1 h-4 w-4" />
          </a>
        ) : (
          '-'
        ),
    },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Retailers</h1>
              <p className="text-gray-500">
                Manage monitored retailers ({retailers.length} active)
              </p>
            </div>
            <Button icon={RefreshCw} onClick={handleRetry} isLoading={isLoading}>
              Refresh
            </Button>
          </div>

          {error && (
            <div className="mb-6">
              <ApiErrorCard
                error={error}
                onRetry={handleRetry}
                isRetrying={isRetrying}
              />
            </div>
          )}

          <div className="rounded-xl bg-white shadow-sm border border-gray-100">
            <DataTable
              columns={columns}
              data={retailers}
              keyExtractor={(r) => r.id}
              isLoading={isLoading}
              emptyMessage="No retailers found"
            />
          </div>
        </div>
      </main>
    </div>
  );
}
