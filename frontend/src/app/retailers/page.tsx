'use client';

import { useEffect, useState } from 'react';
import { Store, ExternalLink } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { DataTable } from '@/components/DataTable';
import { api, Retailer } from '@/lib/api';

export default function RetailersPage() {
  const [retailers, setRetailers] = useState<Retailer[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchRetailers = async () => {
      try {
        const res = await api.getRetailers();
        setRetailers(res.retailers);
      } catch (error) {
        console.error('Failed to fetch retailers:', error);
      } finally {
        setIsLoading(false);
      }
    };

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
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Retailers</h1>
            <p className="text-gray-500">
              Manage monitored retailers ({retailers.length} active)
            </p>
          </div>

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
