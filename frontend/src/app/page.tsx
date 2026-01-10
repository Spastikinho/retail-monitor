'use client';

import { useEffect, useState } from 'react';
import { Package, Store, Bell, Activity, RefreshCw, Camera } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { StatsCard } from '@/components/StatsCard';
import { Button } from '@/components/Button';
import { api, AnalyticsSummary, AlertEvent } from '@/lib/api';

export default function Dashboard() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<AlertEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [summaryRes, alertsRes] = await Promise.all([
        api.getAnalyticsSummary(),
        api.getAlerts({ limit: 5 }),
      ]);
      setSummary(summaryRes.summary);
      setRecentAlerts(alertsRes.events);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-gray-500">Overview of your retail monitoring</p>
            </div>
            <Button icon={RefreshCw} onClick={fetchData} isLoading={isLoading}>
              Refresh
            </Button>
          </div>

          {error && (
            <div className="mb-6 rounded-lg bg-red-50 p-4 text-red-700">
              {error}
            </div>
          )}

          {isLoading && !summary ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
            </div>
          ) : summary ? (
            <>
              <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <StatsCard
                  title="Total Products"
                  value={summary.products.total}
                  icon={Package}
                  description={`${summary.products.own} own, ${summary.products.competitors} competitors`}
                />
                <StatsCard
                  title="Active Listings"
                  value={summary.listings}
                  icon={Store}
                />
                <StatsCard
                  title="Alerts (7d)"
                  value={summary.recent_activity.alerts_7d}
                  icon={Bell}
                />
                <StatsCard
                  title="Snapshots (7d)"
                  value={summary.recent_activity.snapshots_7d}
                  icon={Camera}
                />
              </div>

              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <h2 className="mb-4 text-lg font-semibold text-gray-900">
                    Recent Activity
                  </h2>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4">
                      <div className="flex items-center">
                        <Activity className="mr-3 h-5 w-5 text-primary-600" />
                        <span className="text-sm text-gray-600">
                          Scrape sessions (7d)
                        </span>
                      </div>
                      <span className="font-semibold text-gray-900">
                        {summary.recent_activity.sessions_7d}
                      </span>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-gray-50 p-4">
                      <div className="flex items-center">
                        <Camera className="mr-3 h-5 w-5 text-green-600" />
                        <span className="text-sm text-gray-600">
                          New reviews (7d)
                        </span>
                      </div>
                      <span className="font-semibold text-gray-900">
                        {summary.recent_activity.reviews_7d}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <h2 className="mb-4 text-lg font-semibold text-gray-900">
                    Recent Alerts
                  </h2>
                  {recentAlerts.length === 0 ? (
                    <p className="text-gray-500">No recent alerts</p>
                  ) : (
                    <div className="space-y-3">
                      {recentAlerts.map((alert) => (
                        <div
                          key={alert.id}
                          className="rounded-lg border border-gray-200 p-3"
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <p className="font-medium text-gray-900">
                                {alert.rule_name}
                              </p>
                              <p className="text-sm text-gray-500">
                                {alert.product} - {alert.retailer}
                              </p>
                            </div>
                            <span
                              className={`rounded-full px-2 py-1 text-xs font-medium ${
                                alert.is_delivered
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-yellow-100 text-yellow-700'
                              }`}
                            >
                              {alert.is_delivered ? 'Delivered' : 'Pending'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : null}
        </div>
      </main>
    </div>
  );
}
