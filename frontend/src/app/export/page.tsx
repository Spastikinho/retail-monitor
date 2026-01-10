'use client';

import { useEffect, useState } from 'react';
import { Download, FileSpreadsheet, Calendar, Package } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/Button';
import { api, MonitoringPeriod, ManualImport } from '@/lib/api';

export default function ExportPage() {
  const [periods, setPeriods] = useState<MonitoringPeriod[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [imports, setImports] = useState<ManualImport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [periodsRes, importsRes] = await Promise.all([
          api.getPeriods(),
          api.getImports({ status: 'completed', limit: 100 }),
        ]);
        setPeriods(periodsRes.periods);
        setImports(importsRes.imports);
        if (periodsRes.periods.length > 0) {
          setSelectedPeriod(periodsRes.periods[0].period);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleDownloadMonitoring = () => {
    const url = api.getExportMonitoringUrl(selectedPeriod || undefined);
    window.open(url, '_blank');
  };

  const handleDownloadAll = () => {
    const url = api.getExportMonitoringUrl();
    window.open(url, '_blank');
  };

  const handleDownloadSingle = (importId: string) => {
    const url = api.getExportImportUrl(importId);
    window.open(url, '_blank');
  };

  const ownProducts = imports.filter(i => i.product_type === 'own');
  const competitorProducts = imports.filter(i => i.product_type === 'competitor');

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Export Data</h1>
            <p className="text-gray-500">Download monitoring data as Excel spreadsheets</p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
            </div>
          ) : (
            <>
              {/* Quick Export Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                {/* Export by Period */}
                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-4">
                    <Calendar className="h-8 w-8 text-primary-600 mr-3" />
                    <div>
                      <h3 className="font-semibold text-gray-900">Export by Period</h3>
                      <p className="text-sm text-gray-500">Download data for specific month</p>
                    </div>
                  </div>

                  {periods.length > 0 ? (
                    <>
                      <select
                        value={selectedPeriod}
                        onChange={(e) => setSelectedPeriod(e.target.value)}
                        className="w-full mb-4 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      >
                        {periods.map((p) => (
                          <option key={p.period} value={p.period}>
                            {p.label} ({p.count} products)
                          </option>
                        ))}
                      </select>
                      <Button onClick={handleDownloadMonitoring} icon={Download} className="w-full">
                        Download Excel
                      </Button>
                    </>
                  ) : (
                    <p className="text-gray-500 text-sm">No periods available</p>
                  )}
                </div>

                {/* Export All Data */}
                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-4">
                    <FileSpreadsheet className="h-8 w-8 text-green-600 mr-3" />
                    <div>
                      <h3 className="font-semibold text-gray-900">Export All Data</h3>
                      <p className="text-sm text-gray-500">Complete monitoring export</p>
                    </div>
                  </div>

                  <div className="mb-4">
                    <p className="text-2xl font-bold text-gray-900">{imports.length}</p>
                    <p className="text-sm text-gray-500">Total completed imports</p>
                  </div>

                  <Button onClick={handleDownloadAll} icon={Download} variant="secondary" className="w-full">
                    Download All
                  </Button>
                </div>

                {/* Stats Card */}
                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <div className="flex items-center mb-4">
                    <Package className="h-8 w-8 text-yellow-600 mr-3" />
                    <div>
                      <h3 className="font-semibold text-gray-900">Summary</h3>
                      <p className="text-sm text-gray-500">Data breakdown</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Our Products</span>
                      <span className="font-medium text-green-600">{ownProducts.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Competitor Products</span>
                      <span className="font-medium text-yellow-600">{competitorProducts.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Available Periods</span>
                      <span className="font-medium text-primary-600">{periods.length}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Individual Product Exports */}
              <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Export Individual Products</h2>

                {imports.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No completed imports available</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200">
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Product</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Retailer</th>
                          <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Type</th>
                          <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Price</th>
                          <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Reviews</th>
                          <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Export</th>
                        </tr>
                      </thead>
                      <tbody>
                        {imports.slice(0, 20).map((imp) => (
                          <tr key={imp.id} className="border-b border-gray-100 hover:bg-gray-50">
                            <td className="py-3 px-4">
                              <p className="font-medium text-gray-900 truncate max-w-xs">
                                {imp.product_title || imp.custom_name || imp.url.slice(0, 40)}
                              </p>
                            </td>
                            <td className="py-3 px-4 text-gray-600">{imp.retailer || '-'}</td>
                            <td className="py-3 px-4">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                imp.product_type === 'own'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-yellow-100 text-yellow-700'
                              }`}>
                                {imp.product_type === 'own' ? 'Our' : 'Competitor'}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right font-medium">
                              {imp.price_final ? `${imp.price_final.toFixed(2)} ₽` : '-'}
                            </td>
                            <td className="py-3 px-4 text-right">
                              {imp.reviews_count ?? '-'}
                            </td>
                            <td className="py-3 px-4 text-center">
                              <button
                                onClick={() => handleDownloadSingle(imp.id)}
                                className="inline-flex items-center text-primary-600 hover:text-primary-700"
                                title="Download Excel"
                              >
                                <Download className="h-5 w-5" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
