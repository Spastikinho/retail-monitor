'use client';

import { useEffect, useState } from 'react';
import { Upload, Link, CheckCircle, XCircle, Clock, Loader2, Download } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/Button';
import { api, ManualImport } from '@/lib/api';

export default function ImportPage() {
  const [urls, setUrls] = useState('');
  const [productType, setProductType] = useState<'own' | 'competitor'>('competitor');
  const [imports, setImports] = useState<ManualImport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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

    const urlList = urls
      .split('\n')
      .map(u => u.trim())
      .filter(u => u.length > 0);

    if (urlList.length === 0) {
      setError('Please enter at least one URL');
      return;
    }

    if (urlList.length > 20) {
      setError('Maximum 20 URLs per request');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await api.createImports({
        urls: urlList,
        product_type: productType,
      });

      if (res.errors && res.errors.length > 0) {
        setError(`Warnings: ${res.errors.join(', ')}`);
      }

      setSuccess(`Created ${res.imports.length} import(s). Processing...`);
      setUrls('');
      fetchImports();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create imports');
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
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Product URLs (one per line, max 20)
                </label>
                <textarea
                  value={urls}
                  onChange={(e) => setUrls(e.target.value)}
                  className="w-full h-40 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="https://www.ozon.ru/product/...&#10;https://www.wildberries.ru/catalog/...&#10;https://www.perekrestok.ru/cat/..."
                />
                <p className="mt-1 text-sm text-gray-500">
                  Supported: Ozon, Wildberries, Perekrestok, VkusVill, Yandex Lavka
                </p>
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
                <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg">
                  {error}
                </div>
              )}

              {success && (
                <div className="mb-4 p-4 bg-green-50 text-green-700 rounded-lg">
                  {success}
                </div>
              )}

              <Button type="submit" icon={Upload} isLoading={isSubmitting}>
                Import URLs
              </Button>
            </form>
          </div>

          {/* Recent Imports */}
          <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Recent Imports</h2>
              <Button variant="secondary" onClick={fetchImports} isLoading={isLoading}>
                Refresh
              </Button>
            </div>

            {isLoading && imports.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
              </div>
            ) : imports.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No imports yet</p>
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
                      <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Reviews</th>
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
                            <p className="font-medium text-gray-900 truncate">
                              {imp.product_title || imp.custom_name || 'Processing...'}
                            </p>
                            <a
                              href={imp.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm text-primary-600 hover:underline flex items-center"
                            >
                              <Link className="h-3 w-3 mr-1" />
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
                              <span className="font-medium">{imp.price_final.toFixed(2)} ₽</span>
                              {imp.price_change && (
                                <span className={`block text-sm ${imp.price_change > 0 ? 'text-red-600' : 'text-green-600'}`}>
                                  {imp.price_change > 0 ? '+' : ''}{imp.price_change.toFixed(2)}
                                </span>
                              )}
                            </div>
                          ) : '-'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {imp.rating ? imp.rating.toFixed(1) : '-'}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {imp.reviews_count ?? '-'}
                          {imp.reviews_negative > 0 && (
                            <span className="block text-sm text-red-600">
                              -{imp.reviews_negative} negative
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {imp.status === 'completed' && (
                            <a
                              href={api.getExportImportUrl(imp.id)}
                              className="inline-flex items-center text-primary-600 hover:text-primary-700"
                              title="Download Excel"
                            >
                              <Download className="h-4 w-4" />
                            </a>
                          )}
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
