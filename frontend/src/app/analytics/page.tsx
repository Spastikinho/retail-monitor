'use client';

import { useEffect, useState } from 'react';
import { BarChart3, TrendingUp, Package, Store, RefreshCw } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { StatsCard } from '@/components/StatsCard';
import { Button } from '@/components/Button';
import { ApiErrorCard, createApiErrorInfo, logApiError, ApiErrorInfo } from '@/components/ApiErrorCard';
import { api, AnalyticsSummary } from '@/lib/api';

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiErrorInfo | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const fetchSummary = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getAnalyticsSummary();
      setSummary(res.summary);
    } catch (err) {
      const errorInfo = createApiErrorInfo('Loading analytics', err, '/api/v1/analytics/summary/');
      logApiError(errorInfo);
      setError(errorInfo);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    await fetchSummary();
    setIsRetrying(false);
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
              <p className="text-gray-500">Insights and statistics</p>
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

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
            </div>
          ) : summary ? (
            <>
              <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <StatsCard
                  title="Own Products"
                  value={summary.products.own}
                  icon={Package}
                />
                <StatsCard
                  title="Competitor Products"
                  value={summary.products.competitors}
                  icon={TrendingUp}
                />
                <StatsCard
                  title="Active Listings"
                  value={summary.listings}
                  icon={Store}
                />
                <StatsCard
                  title="Weekly Snapshots"
                  value={summary.recent_activity.snapshots_7d}
                  icon={BarChart3}
                />
              </div>

              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <h2 className="mb-4 text-lg font-semibold text-gray-900">
                    Product Distribution
                  </h2>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Own Products</span>
                        <span className="font-medium">
                          {summary.products.own}
                        </span>
                      </div>
                      <div className="mt-2 h-2 rounded-full bg-gray-200">
                        <div
                          className="h-2 rounded-full bg-blue-500"
                          style={{
                            width: `${
                              (summary.products.own / summary.products.total) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Competitors</span>
                        <span className="font-medium">
                          {summary.products.competitors}
                        </span>
                      </div>
                      <div className="mt-2 h-2 rounded-full bg-gray-200">
                        <div
                          className="h-2 rounded-full bg-orange-500"
                          style={{
                            width: `${
                              (summary.products.competitors /
                                summary.products.total) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <h2 className="mb-4 text-lg font-semibold text-gray-900">
                    Weekly Activity
                  </h2>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4">
                      <span className="text-gray-600">Price Snapshots</span>
                      <span className="text-xl font-bold text-gray-900">
                        {summary.recent_activity.snapshots_7d}
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4">
                      <span className="text-gray-600">New Reviews</span>
                      <span className="text-xl font-bold text-gray-900">
                        {summary.recent_activity.reviews_7d}
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4">
                      <span className="text-gray-600">Alerts Triggered</span>
                      <span className="text-xl font-bold text-gray-900">
                        {summary.recent_activity.alerts_7d}
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4">
                      <span className="text-gray-600">Scrape Sessions</span>
                      <span className="text-xl font-bold text-gray-900">
                        {summary.recent_activity.sessions_7d}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : !error ? (
            <p className="text-gray-500">No analytics data available</p>
          ) : null}
        </div>
      </main>
    </div>
  );
}
