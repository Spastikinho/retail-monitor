'use client';

import { useEffect, useState } from 'react';
import { Bell, CheckCircle, Clock } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { DataTable } from '@/components/DataTable';
import { Button } from '@/components/Button';
import { api, AlertEvent } from '@/lib/api';
import { format } from 'date-fns';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'delivered'>('all');

  const fetchAlerts = async () => {
    setIsLoading(true);
    try {
      const params: { delivered?: boolean } = {};
      if (filter === 'pending') params.delivered = false;
      if (filter === 'delivered') params.delivered = true;

      const res = await api.getAlerts({ ...params, limit: 100 });
      setAlerts(res.events);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [filter]);

  const columns = [
    {
      key: 'rule_name',
      header: 'Alert Rule',
      render: (alert: AlertEvent) => (
        <div className="flex items-center">
          <Bell className="mr-3 h-5 w-5 text-yellow-500" />
          <div>
            <p className="font-medium text-gray-900">{alert.rule_name}</p>
            <p className="text-sm text-gray-500">{alert.alert_type}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'product',
      header: 'Product',
      render: (alert: AlertEvent) => (
        <div>
          <p className="text-gray-900">{alert.product}</p>
          <p className="text-sm text-gray-500">{alert.retailer}</p>
        </div>
      ),
    },
    {
      key: 'message',
      header: 'Message',
      render: (alert: AlertEvent) => (
        <p className="max-w-md truncate text-gray-600">{alert.message}</p>
      ),
    },
    {
      key: 'triggered_at',
      header: 'Triggered',
      render: (alert: AlertEvent) =>
        format(new Date(alert.triggered_at), 'dd.MM.yyyy HH:mm'),
    },
    {
      key: 'is_delivered',
      header: 'Status',
      render: (alert: AlertEvent) => (
        <span
          className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
            alert.is_delivered
              ? 'bg-green-100 text-green-700'
              : 'bg-yellow-100 text-yellow-700'
          }`}
        >
          {alert.is_delivered ? (
            <>
              <CheckCircle className="mr-1 h-3 w-3" />
              Delivered
            </>
          ) : (
            <>
              <Clock className="mr-1 h-3 w-3" />
              Pending
            </>
          )}
        </span>
      ),
    },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
            <p className="text-gray-500">Monitor price changes and notifications</p>
          </div>

          <div className="mb-6 flex gap-2">
            <Button
              variant={filter === 'all' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('all')}
            >
              All
            </Button>
            <Button
              variant={filter === 'pending' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('pending')}
            >
              Pending
            </Button>
            <Button
              variant={filter === 'delivered' ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setFilter('delivered')}
            >
              Delivered
            </Button>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-100">
            <DataTable
              columns={columns}
              data={alerts}
              keyExtractor={(a) => a.id}
              isLoading={isLoading}
              emptyMessage="No alerts found"
            />
          </div>
        </div>
      </main>
    </div>
  );
}
