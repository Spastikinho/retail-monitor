'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Upload,
  Link as LinkIcon,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Download,
  RefreshCw,
  AlertTriangle,
  Eye,
} from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/Button';
import { SkeletonTable, Skeleton } from '@/components/Skeleton';
import { api, ManualImport } from '@/lib/api';
import {
  validateUrls,
  ValidationError,
  ValidationResult,
  getSupportedRetailerNames,
} from '@/lib/url-validation';

export default function ImportPage() {
  const router = useRouter();
  const [urls, setUrls] = useState('');
  const [productType, setProductType] = useState<'own' | 'competitor'>('competitor');
  const [imports, setImports] = useState<ManualImport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Real-time URL validation
  const validation = useMemo(() => {
    if (!urls.trim()) {
      return { valid: [], invalid: [], total: 0, validCount: 0, invalidCount: 0 };
    }
    return validateUrls(urls);
  }, [urls]);

  const fetchImports = async () => {
    setIsLoading(true);
    try {
      const res = await api.getImports({ limit: 50 });
      setImports(res.imports);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load imports');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchImports();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Use validated URLs
    if (validation.validCount === 0) {
      setError('Please enter at least one valid URL');
      return;
    }

    if (validation.validCount > 20) {
      setError('Maximum 20 URLs per request');
      return;
    }

    // Show warning for invalid URLs
    if (validation.invalidCount > 0) {
      const proceed = window.confirm(
        `${validation.invalidCount} URL(s) are invalid and will be skipped. Continue with ${validation.validCount} valid URL(s)?`
      );
      if (!proceed) return;
    }

    setIsSubmitting(true);
    try {
      const validUrls = validation.valid.map(v => v.url);
      const res = await api.createImports({
        urls: validUrls,
        product_type: productType,
      });

      if (res.errors && res.errors.length > 0) {
        setError(`Warnings: ${res.errors.join(', ')}`);
      }

      setSuccess(`Created ${res.imports.length} import(s). Processing...`);
      setUrls('');

      // Navigate to first import if single URL
      if (res.imports.length === 1) {
        router.push(`/import/${res.imports[0].id}`);
      } else {
        fetchImports();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create imports');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetryFailed = async () => {
    const failedImports = imports.filter(imp => imp.status === 'failed');
    if (failedImports.length === 0) {
      setError('No failed imports to retry');
      return;
    }

    setIsSubmitting(true);
    try {
      const urls = failedImports.map(imp => imp.url);
      const res = await api.createImports({
        urls,
        product_type: failedImports[0].product_type,
      });

      setSuccess(`Retrying ${res.imports.length} failed import(s)`);
      fetchImports();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry imports');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
      processing: 'bg-blue-100 text-blue-700',
      pending: 'bg-gray-100 text-gray-700',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
        {status}
      </span>
    );
  };

  const failedCount = imports.filter(imp => imp.status === 'failed').length;
  const processingCount = imports.filter(imp => imp.status === 'processing' || imp.status === 'pending').length;

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Import URLs</h1>
            <p className="text-gray-500">Add product URLs from supported retailers for price monitoring</p>
          </div>

          {/* Import Form */}
          <div className="mb-8 rounded-xl bg-white p-6 shadow-sm border border-gray-100">
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Product URLs (one per line, max 20)
                  </label>
                  {validation.total > 0 && (
                    <span className="text-sm">
                      <span className="text-green-600">{validation.validCount} valid</span>
                      {validation.invalidCount > 0 && (
                        <span className="text-red-600 ml-2">{validation.invalidCount} invalid</span>
                      )}
                    </span>
                  )}
                </div>
                <textarea
                  value={urls}
                  onChange={(e) => setUrls(e.target.value)}
                  className={`w-full h-40 px-4 py-3 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 ${
                    validation.invalidCount > 0 ? 'border-yellow-400' : 'border-gray-300'
                  }`}
                  placeholder={`https://www.ozon.ru/product/...\nhttps://www.wildberries.ru/catalog/...\nhttps://www.perekrestok.ru/cat/...`}
                />
                <p className="mt-1 text-sm text-gray-500">
                  Supported: {getSupportedRetailerNames().join(', ')}
                </p>

                {/* Validation Errors */}
                {validation.invalidCount > 0 && (
                  <div className="mt-2 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                    <div className="flex items-start">
                      <AlertTriangle className="h-5 w-5 text-yellow-500 mr-2 flex-shrink-0 mt-0.5" />
                      <div className="text-sm">
                        <p className="font-medium text-yellow-800">Validation Issues:</p>
                        <ul className="mt-1 text-yellow-700 space-y-1">
                          {validation.invalid.slice(0, 5).map((err, i) => (
                            <li key={i}>
                              Line {err.line}: {err.error}
                              {err.suggestion && (
                                <span className="text-yellow-600"> - {err.suggestion}</span>
                              )}
                            </li>
                          ))}
                          {validation.invalid.length > 5 && (
                            <li>...and {validation.invalid.length - 5} more</li>
                          )}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}

                {/* Valid URLs Preview */}
                {validation.validCount > 0 && validation.validCount <= 5 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {validation.valid.map((v, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center px-2 py-1 bg-green-50 text-green-700 text-xs rounded-full"
                      >
                        <CheckCircle className="h-3 w-3 mr-1" />
                        {v.retailer?.name || 'Unknown'}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Product Type
                </label>
                <div className="flex space-x-4">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="own"
                      checked={productType === 'own'}
                      onChange={() => setProductType('own')}
                      className="mr-2"
                    />
                    <span>Our Products</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="competitor"
                      checked={productType === 'competitor'}
                      onChange={() => setProductType('competitor')}
                      className="mr-2"
                    />
                    <span>Competitor Products</span>
                  </label>
                </div>
              </div>

              {error && (
                <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-start">
                  <XCircle className="h-5 w-5 mr-2 flex-shrink-0 mt-0.5" />
                  {error}
                </div>
              )}

              {success && (
                <div className="mb-4 p-4 bg-green-50 text-green-700 rounded-lg flex items-start">
                  <CheckCircle className="h-5 w-5 mr-2 flex-shrink-0 mt-0.5" />
                  {success}
                </div>
              )}

              <Button
                type="submit"
                icon={Upload}
                isLoading={isSubmitting}
                disabled={validation.validCount === 0}
              >
                Import {validation.validCount > 0 ? `${validation.validCount} URL(s)` : 'URLs'}
              </Button>
            </form>
          </div>

          {/* Recent Imports */}
          <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-4">
                <h2 className="text-lg font-semibold text-gray-900">Recent Imports</h2>
                {processingCount > 0 && (
                  <span className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    {processingCount} processing
                  </span>
                )}
                {failedCount > 0 && (
                  <span className="inline-flex items-center px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full">
                    {failedCount} failed
                  </span>
                )}
              </div>

              <div className="flex items-center space-x-2">
                {failedCount > 0 && (
                  <Button
                    variant="secondary"
                    onClick={handleRetryFailed}
                    isLoading={isSubmitting}
                    icon={RefreshCw}
                  >
                    Retry Failed ({failedCount})
                  </Button>
                )}
                <Button variant="secondary" onClick={fetchImports} isLoading={isLoading}>
                  Refresh
                </Button>
              </div>
            </div>

            {isLoading && imports.length === 0 ? (
              <SkeletonTable rows={5} columns={7} />
            ) : imports.length === 0 ? (
              <div className="text-center py-12">
                <Upload className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">No imports yet</p>
                <p className="text-sm text-gray-400 mt-1">Add URLs above to start monitoring</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Product</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Retailer</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Type</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Price</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Rating</th>
                      <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {imports.map((imp) => (
                      <tr key={imp.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4">
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(imp.status)}
                            {getStatusBadge(imp.status)}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="max-w-xs">
                            <Link
                              href={`/import/${imp.id}`}
                              className="font-medium text-gray-900 hover:text-primary-600 truncate block"
                            >
                              {imp.product_title || imp.custom_name || 'Processing...'}
                            </Link>
                            <a
                              href={imp.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm text-primary-600 hover:underline flex items-center"
                            >
                              <LinkIcon className="h-3 w-3 mr-1" />
                              View on site
                            </a>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-gray-600">
                          {imp.retailer || '-'}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            imp.product_type === 'own'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {imp.product_type === 'own' ? 'Our' : 'Competitor'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          {imp.price_final ? (
                            <div>
                              <span className="font-medium">{imp.price_final.toFixed(2)} RUB</span>
                              {imp.price_change !== null && imp.price_change !== 0 && (
                                <span className={`block text-sm ${imp.price_change > 0 ? 'text-red-600' : 'text-green-600'}`}>
                                  {imp.price_change > 0 ? '+' : ''}{imp.price_change.toFixed(2)}
                                </span>
                              )}
                            </div>
                          ) : '-'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div>
                            {imp.rating ? imp.rating.toFixed(1) : '-'}
                            {imp.reviews_negative > 0 && (
                              <span className="block text-sm text-red-600">
                                -{imp.reviews_negative} neg
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center justify-center space-x-2">
                            <Link
                              href={`/import/${imp.id}`}
                              className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                              title="View Details"
                            >
                              <Eye className="h-4 w-4" />
                            </Link>
                            {imp.status === 'completed' && (
                              <a
                                href={api.getExportImportUrl(imp.id)}
                                className="p-2 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-lg"
                                title="Download Excel"
                              >
                                <Download className="h-4 w-4" />
                              </a>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
