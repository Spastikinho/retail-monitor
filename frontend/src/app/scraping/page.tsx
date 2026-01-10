'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, Play, CheckCircle, XCircle, Clock } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/Button';
import { api, Retailer } from '@/lib/api';

export default function ScrapingPage() {
  const [retailers, setRetailers] = useState<Retailer[]>([]);
  const [selectedRetailer, setSelectedRetailer] = useState<string>('');
  const [isStarting, setIsStarting] = useState(false);
  const [lastSession, setLastSession] = useState<{
    id: string;
    status: string;
    listings_total: number;
    listings_success: number;
    listings_failed: number;
  } | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const fetchRetailers = async () => {
      try {
        const res = await api.getRetailers();
        setRetailers(res.retailers);
      } catch (error) {
        console.error('Failed to fetch retailers:', error);
      }
    };

    fetchRetailers();
  }, []);

  const handleStartScrape = async () => {
    setIsStarting(true);
    setMessage('');

    try {
      const params = selectedRetailer ? { retailer_id: selectedRetailer } : {};
      const res = await api.triggerScrape(params);
      setMessage(res.message);

      if (res.session_id) {
        // Poll for status
        const pollStatus = async () => {
          const statusRes = await api.getScrapeStatus(res.session_id!);
          setLastSession(statusRes.session);

          if (statusRes.session.status === 'running') {
            setTimeout(pollStatus, 2000);
          }
        };

        pollStatus();
      }
    } catch (error) {
      setMessage('Failed to start scraping session');
    } finally {
      setIsStarting(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'running':
        return <RefreshCw className="h-5 w-5 animate-spin text-blue-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Scraping</h1>
            <p className="text-gray-500">Trigger and monitor scraping sessions</p>
          </div>

          <div className="mb-8 rounded-xl bg-white p-6 shadow-sm border border-gray-100">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              Start New Session
            </h2>

            <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
              <div className="flex-1">
                <label
                  htmlFor="retailer"
                  className="block text-sm font-medium text-gray-700"
                >
                  Retailer (optional)
                </label>
                <select
                  id="retailer"
                  value={selectedRetailer}
                  onChange={(e) => setSelectedRetailer(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  <option value="">All Retailers</option>
                  {retailers.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>

              <Button
                onClick={handleStartScrape}
                isLoading={isStarting}
                icon={Play}
              >
                Start Scraping
              </Button>
            </div>

            {message && (
              <p className="mt-4 text-sm text-gray-600">{message}</p>
            )}
          </div>

          {lastSession && (
            <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">
                Session Status
              </h2>

              <div className="flex items-center gap-3 mb-4">
                {getStatusIcon(lastSession.status)}
                <span className="font-medium capitalize">
                  {lastSession.status}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-gray-50 p-4 text-center">
                  <p className="text-2xl font-bold text-gray-900">
                    {lastSession.listings_total}
                  </p>
                  <p className="text-sm text-gray-500">Total</p>
                </div>
                <div className="rounded-lg bg-green-50 p-4 text-center">
                  <p className="text-2xl font-bold text-green-600">
                    {lastSession.listings_success}
                  </p>
                  <p className="text-sm text-gray-500">Success</p>
                </div>
                <div className="rounded-lg bg-red-50 p-4 text-center">
                  <p className="text-2xl font-bold text-red-600">
                    {lastSession.listings_failed}
                  </p>
                  <p className="text-sm text-gray-500">Failed</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
