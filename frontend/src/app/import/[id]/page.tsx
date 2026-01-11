'use client';

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
  Download,
  ExternalLink,
  AlertTriangle,
} from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/Button';
import { SkeletonImportDetail, Skeleton } from '@/components/Skeleton';
import { api, ManualImportDetail } from '@/lib/api';
import { usePolling } from '@/lib/use-polling';

type ImportStatus = 'pending' | 'processing' | 'completed' | 'failed';

export default function ImportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const importId = params.id as string;

  const [importData, setImportData] = useState<ManualImportDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const fetchImport = useCallback(async () => {
    const res = await api.getImport(importId);
    return res.import;
  }, [importId]);

  // Use polling for processing imports
  const { data: polledData, isPolling } = usePolling<ManualImportDetail>({
    fetcher: fetchImport,
    stopCondition: (data) => data.status === 'completed' || data.status === 'failed',
    initialInterval: 2000,
    maxInterval: 10000,
    backoffMultiplier: 1.3,
    enabled: importData?.status === 'pending' || importData?.status === 'processing',
    onSuccess: (data) => setImportData(data),
    onError: (err) => console.error('Polling error:', err),
  });

  // Initial fetch
  useEffect(() => {
    const loadImport = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await fetchImport();
        setImportData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load import');
      } finally {
        setIsLoading(false);
      }
    };

    loadImport();
  }, [fetchImport]);

  // Update from polling
  useEffect(() => {
    if (polledData) {
      setImportData(polledData);
    }
  }, [polledData]);

  const handleRetry = async () => {
    if (!importData) return;

    setIsRetrying(true);
    try {
      // Create a new import with the same URL
      const res = await api.createImports({
        urls: [importData.url],
        product_type: importData.product_type,
        group_id: importData.group?.id,
      });

      if (res.imports.length > 0) {
        // Navigate to the new import
        router.push(`/import/${res.imports[0].id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry');
    } finally {
      setIsRetrying(false);
    }
  };

  const getStatusIcon = (status: ImportStatus) => {
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

  const getStatusColor = (status: ImportStatus) => {
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
          {isLoading && <SkeletonImportDetail />}

          {/* Error State */}
          {error && !isLoading && (
            <div className="rounded-xl bg-red-50 p-6 border border-red-200">
              <div className="flex items-center space-x-3">
                <AlertTriangle className="h-6 w-6 text-red-500" />
                <div>
                  <h3 className="font-medium text-red-800">Error loading import</h3>
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
          {importData && !isLoading && (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">
                    {importData.product_title || importData.custom_name || 'Import Details'}
                  </h1>
                  <a
                    href={importData.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:underline flex items-center mt-1"
                  >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    {importData.retailer || 'View on site'}
                  </a>
                </div>

                <div className="flex items-center space-x-3">
                  {isPolling && (
                    <span className="text-sm text-gray-500 flex items-center">
                      <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                      Updating...
                    </span>
                  )}

                  {importData.status === 'completed' && (
                    <a
                      href={api.getExportImportUrl(importId)}
                      className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Export Excel
                    </a>
                  )}

                  {importData.status === 'failed' && (
                    <Button
                      onClick={handleRetry}
                      isLoading={isRetrying}
                      icon={RefreshCw}
                    >
                      Retry
                    </Button>
                  )}
                </div>
              </div>

              {/* Status Card */}
              <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">Status</h2>
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(importData.status)}
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(importData.status)}`}>
                      {importData.status}
                    </span>
                  </div>
                </div>

                {/* Progress Bar for Processing */}
                {(importData.status === 'pending' || importData.status === 'processing') && (
                  <div className="mb-6">
                    <div className="flex justify-between text-sm text-gray-600 mb-2">
                      <span>Processing...</span>
                      <span>Please wait</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full animate-pulse w-full" />
                    </div>
                  </div>
                )}

                {/* Error Message */}
                {importData.status === 'failed' && importData.error_message && (
                  <div className="mb-6 p-4 bg-red-50 rounded-lg border border-red-200">
                    <p className="text-red-700">{importData.error_message}</p>
                  </div>
                )}

                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="rounded-lg bg-gray-50 p-4">
                    <p className="text-sm text-gray-500">Price</p>
                    <p className="text-xl font-bold text-gray-900">
                      {formatPrice(importData.price_final)}
                    </p>
                    {importData.price_change !== null && importData.price_change !== 0 && (
                      <p className={`text-sm ${importData.price_change > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {importData.price_change > 0 ? '+' : ''}{formatPrice(importData.price_change)}
                        {importData.price_change_pct && ` (${importData.price_change_pct.toFixed(1)}%)`}
                      </p>
                    )}
                  </div>

                  <div className="rounded-lg bg-gray-50 p-4">
                    <p className="text-sm text-gray-500">Rating</p>
                    <p className="text-xl font-bold text-gray-900">
                      {importData.rating?.toFixed(1) || '-'}
                    </p>
                    <p className="text-sm text-gray-500">
                      {importData.reviews_count ?? 0} reviews
                    </p>
                  </div>

                  <div className="rounded-lg bg-gray-50 p-4">
                    <p className="text-sm text-gray-500">In Stock</p>
                    <p className="text-xl font-bold text-gray-900">
                      {importData.in_stock === null ? '-' : importData.in_stock ? 'Yes' : 'No'}
                    </p>
                  </div>

                  <div className="rounded-lg bg-gray-50 p-4">
                    <p className="text-sm text-gray-500">Type</p>
                    <p className="text-xl font-bold text-gray-900 capitalize">
                      {importData.product_type === 'own' ? 'Our Product' : 'Competitor'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Price Details */}
              {importData.status === 'completed' && (
                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Price Details</h2>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">Regular Price</p>
                      <p className="text-lg font-medium">{formatPrice(importData.price_regular)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Promo Price</p>
                      <p className="text-lg font-medium">{formatPrice(importData.price_promo)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Final Price</p>
                      <p className="text-lg font-medium text-primary-600">{formatPrice(importData.price_final)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Previous Price</p>
                      <p className="text-lg font-medium">{formatPrice(importData.price_previous)}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Reviews Summary */}
              {importData.status === 'completed' && importData.reviews_count !== null && importData.reviews_count > 0 && (
                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Reviews Summary</h2>

                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="rounded-lg bg-green-50 p-4 text-center">
                      <p className="text-2xl font-bold text-green-600">{importData.reviews_positive}</p>
                      <p className="text-sm text-gray-600">Positive</p>
                    </div>
                    <div className="rounded-lg bg-gray-50 p-4 text-center">
                      <p className="text-2xl font-bold text-gray-600">{importData.reviews_neutral}</p>
                      <p className="text-sm text-gray-600">Neutral</p>
                    </div>
                    <div className="rounded-lg bg-red-50 p-4 text-center">
                      <p className="text-2xl font-bold text-red-600">{importData.reviews_negative}</p>
                      <p className="text-sm text-gray-600">Negative</p>
                    </div>
                  </div>

                  {/* Review Insights */}
                  {importData.review_insights && Object.keys(importData.review_insights).length > 0 && (
                    <div className="mb-6">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">Key Insights</h3>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <pre className="text-sm text-gray-600 whitespace-pre-wrap">
                          {JSON.stringify(importData.review_insights, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Sample Reviews */}
                  {importData.reviews_data && importData.reviews_data.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2">
                        Recent Reviews ({importData.reviews_data.length})
                      </h3>
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {importData.reviews_data.slice(0, 10).map((review, index) => (
                          <div key={index} className="p-4 bg-gray-50 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-gray-900">{review.author || 'Anonymous'}</span>
                              <div className="flex items-center">
                                <span className="text-yellow-500">{'★'.repeat(review.rating)}</span>
                                <span className="text-gray-300">{'★'.repeat(5 - review.rating)}</span>
                              </div>
                            </div>
                            <p className="text-gray-600 text-sm">{review.text}</p>
                            {review.pros && (
                              <p className="text-green-600 text-sm mt-1">+ {review.pros}</p>
                            )}
                            {review.cons && (
                              <p className="text-red-600 text-sm mt-1">- {review.cons}</p>
                            )}
                            <p className="text-gray-400 text-xs mt-2">{review.date}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Metadata */}
              <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Details</h2>
                <dl className="grid grid-cols-2 gap-4">
                  <div>
                    <dt className="text-sm text-gray-500">Created</dt>
                    <dd className="text-gray-900">{formatDate(importData.created_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Processed</dt>
                    <dd className="text-gray-900">{formatDate(importData.processed_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Monitoring Period</dt>
                    <dd className="text-gray-900">{importData.monitoring_period || '-'}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Group</dt>
                    <dd className="text-gray-900">{importData.group?.name || '-'}</dd>
                  </div>
                  {importData.notes && (
                    <div className="col-span-2">
                      <dt className="text-sm text-gray-500">Notes</dt>
                      <dd className="text-gray-900">{importData.notes}</dd>
                    </div>
                  )}
                </dl>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
