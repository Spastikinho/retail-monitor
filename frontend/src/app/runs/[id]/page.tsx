'use client';

/**
 * Run Details Page
 * Phase 5 Implementation - Shows batch run progress with polling
 *
 * Features:
 * - Real-time progress bar with percentage
 * - Incremental results display
 * - Failed items table with error details
 * - Retry failed URLs button
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  Eye,
} from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/Button';
import { SkeletonTable, Skeleton, SkeletonProgressBar, SkeletonStats } from '@/components/Skeleton';
import { api, GetRunResponse, RunItem, Run } from '@/lib/api';
import { usePolling } from '@/lib/use-polling';

type RunStatus = 'pending' | 'processing' | 'completed' | 'failed';

export default function RunDetailPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;

  const [runData, setRunData] = useState<GetRunResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const fetchRun = useCallback(async () => {
    const res = await api.getRun(runId);
    return res;
  }, [runId]);

  // Use polling for processing runs
  const { isPolling } = usePolling<GetRunResponse>({
    fetcher: fetchRun,
    stopCondition: (data) => data.run.status === 'completed' || data.run.status === 'failed',
    initialInterval: 2000,
    maxInterval: 10000,
    backoffMultiplier: 1.3,
    enabled: runData?.run.status === 'pending' || runData?.run.status === 'processing',
    onSuccess: (data) => setRunData(data),
    onError: (err) => console.error('Polling error:', err),
  });

  // Initial fetch
  useEffect(() => {
    const loadRun = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await fetchRun();
        setRunData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load run');
      } finally {
        setIsLoading(false);
      }
    };

    loadRun();
  }, [fetchRun]);

  const handleRetryFailed = async () => {
    if (!runData || runData.errors.length === 0) return;

    setIsRetrying(true);
    try {
      const res = await api.retryRun(runId);
      // Navigate to the new run
      router.push(`/runs/${res.run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry');
    } finally {
      setIsRetrying(false);
    }
  };

  const getStatusIcon = (status: RunStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-6 w-6 text-green-500" />;
      case 'failed':
        return <XCircle className="h-6 w-6 text-red-500" />;
      case 'processing':
        return <Loader2 className="h-6 w-6 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-6 w-6 text-gray-400" />;
    }
  };

  const getStatusColor = (status: RunStatus) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'failed':
        return 'bg-red-100 text-red-700';
      case 'processing':
        return 'bg-blue-100 text-blue-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const formatPrice = (price: number | null) => {
    if (price === null) return '-';
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
    }).format(price);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const run = runData?.run;
  const results = runData?.results || [];
  const errors = runData?.errors || [];

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          {/* Back Button */}
          <Link
            href="/import"
            className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-6"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Imports
          </Link>

          {/* Loading State */}
          {isLoading && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-10 w-32" />
              </div>
              <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                <SkeletonProgressBar />
                <div className="mt-4">
                  <SkeletonStats count={4} />
                </div>
              </div>
              <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                <SkeletonTable rows={5} columns={5} />
              </div>
            </div>
          )}

          {/* Error State */}
          {error && !isLoading && (
            <div className="rounded-xl bg-red-50 p-6 border border-red-200">
              <div className="flex items-center space-x-3">
                <AlertTriangle className="h-6 w-6 text-red-500" />
                <div>
                  <h3 className="font-medium text-red-800">Error loading run</h3>
                  <p className="text-red-600">{error}</p>
                </div>
              </div>
              <Button
                variant="secondary"
                className="mt-4"
                onClick={() => window.location.reload()}
              >
                Try Again
              </Button>
            </div>
          )}

          {/* Content */}
          {run && !isLoading && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">
                    Batch Import Run
                  </h1>
                  <p className="text-gray-500 mt-1">
                    Run ID: {run.id}
                  </p>
                </div>

                <div className="flex items-center space-x-3">
                  {isPolling && (
                    <span className="text-sm text-gray-500 flex items-center">
                      <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                      Updating...
                    </span>
                  )}

                  {errors.length > 0 && run.status !== 'processing' && (
                    <Button
                      onClick={handleRetryFailed}
                      isLoading={isRetrying}
                      icon={RefreshCw}
                    >
                      Retry Failed ({errors.length})
                    </Button>
                  )}
                </div>
              </div>

              {/* Status Card with Progress */}
              <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Progress</h2>
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(run.status as RunStatus)}
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(run.status as RunStatus)}`}>
                      {run.status}
                    </span>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mb-6">
                  <div className="flex justify-between text-sm text-gray-600 mb-2">
                    <span>
                      {run.status === 'completed' || run.status === 'failed'
                        ? `Completed: ${run.progress.completed + run.progress.failed} / ${run.progress.total}`
                        : `Processing: ${run.progress.completed + run.progress.failed} / ${run.progress.total}`}
                    </span>
                    <span>{run.progress.percentage}%</span>
                  </div>
                  <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        run.status === 'failed'
                          ? 'bg-red-500'
                          : run.status === 'completed'
                          ? 'bg-green-500'
                          : 'bg-blue-500'
                      }`}
                      style={{ width: `${run.progress.percentage}%` }}
                    />
                  </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="rounded-lg bg-gray-50 p-4">
                    <p className="text-sm text-gray-500">Total Items</p>
                    <p className="text-2xl font-bold text-gray-900">{run.progress.total}</p>
                  </div>
                  <div className="rounded-lg bg-green-50 p-4">
                    <p className="text-sm text-gray-500">Completed</p>
                    <p className="text-2xl font-bold text-green-600">{run.progress.completed}</p>
                  </div>
                  <div className="rounded-lg bg-red-50 p-4">
                    <p className="text-sm text-gray-500">Failed</p>
                    <p className="text-2xl font-bold text-red-600">{run.progress.failed}</p>
                  </div>
                  <div className="rounded-lg bg-blue-50 p-4">
                    <p className="text-sm text-gray-500">In Progress</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {run.progress.total - run.progress.completed - run.progress.failed}
                    </p>
                  </div>
                </div>
              </div>

              {/* Failed Items Table */}
              {errors.length > 0 && (
                <div className="rounded-xl bg-white p-6 shadow-sm border border-red-100">
                  <h2 className="text-lg font-semibold text-red-800 mb-4 flex items-center">
                    <XCircle className="h-5 w-5 mr-2" />
                    Failed Items ({errors.length})
                  </h2>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">URL</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Retailer</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Error</th>
                          <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {errors.map((item) => (
                          <tr key={item.id} className="border-b border-gray-100 hover:bg-red-50">
                            <td className="py-3 px-4">
                              <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary-600 hover:underline flex items-center text-sm"
                              >
                                <ExternalLink className="h-3 w-3 mr-1 flex-shrink-0" />
                                <span className="truncate max-w-xs">{item.url}</span>
                              </a>
                            </td>
                            <td className="py-3 px-4 text-gray-600 text-sm">
                              {item.retailer || '-'}
                            </td>
                            <td className="py-3 px-4">
                              <span className="text-red-600 text-sm">{item.error_message || 'Unknown error'}</span>
                            </td>
                            <td className="py-3 px-4">
                              <Link
                                href={`/import/${item.id}`}
                                className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg inline-flex"
                                title="View Details"
                              >
                                <Eye className="h-4 w-4" />
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Results Table */}
              {results.length > 0 && (
                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <CheckCircle className="h-5 w-5 mr-2 text-green-500" />
                    Results ({results.filter(r => r.status === 'completed').length})
                  </h2>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Product</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Retailer</th>
                          <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Price</th>
                          <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Rating</th>
                          <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.map((item) => (
                          <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-3 px-4">
                              {item.status === 'completed' ? (
                                <CheckCircle className="h-5 w-5 text-green-500" />
                              ) : item.status === 'processing' ? (
                                <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
                              ) : (
                                <Clock className="h-5 w-5 text-gray-400" />
                              )}
                            </td>
                            <td className="py-3 px-4">
                              <div className="max-w-xs">
                                <Link
                                  href={`/import/${item.id}`}
                                  className="font-medium text-gray-900 hover:text-primary-600 truncate block"
                                >
                                  {item.product_title || 'Processing...'}
                                </Link>
                                <a
                                  href={item.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-primary-600 hover:underline flex items-center"
                                >
                                  <ExternalLink className="h-3 w-3 mr-1" />
                                  View on site
                                </a>
                              </div>
                            </td>
                            <td className="py-3 px-4 text-gray-600 text-sm">
                              {item.retailer || '-'}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <span className="font-medium">{formatPrice(item.price_final)}</span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              {item.rating ? (
                                <div className="flex items-center justify-end">
                                  <span className="text-yellow-500 mr-1">★</span>
                                  <span>{item.rating.toFixed(1)}</span>
                                  {item.reviews_count && (
                                    <span className="text-gray-400 text-xs ml-1">({item.reviews_count})</span>
                                  )}
                                </div>
                              ) : '-'}
                            </td>
                            <td className="py-3 px-4">
                              <Link
                                href={`/import/${item.id}`}
                                className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg inline-flex"
                                title="View Details"
                              >
                                <Eye className="h-4 w-4" />
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Timestamps */}
              <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Timestamps</h2>
                <dl className="grid grid-cols-3 gap-4">
                  <div>
                    <dt className="text-sm text-gray-500">Created</dt>
                    <dd className="text-gray-900">{formatDate(run.created_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Started</dt>
                    <dd className="text-gray-900">{formatDate(run.started_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Finished</dt>
                    <dd className="text-gray-900">{formatDate(run.finished_at)}</dd>
                  </div>
                </dl>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
