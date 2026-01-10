'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Filter, Package } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { DataTable } from '@/components/DataTable';
import { Button } from '@/components/Button';
import { api, Product } from '@/lib/api';

export default function ProductsPage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'own' | 'competitors'>('all');

  const fetchProducts = async () => {
    setIsLoading(true);
    try {
      const params: { search?: string; is_own?: boolean } = {};
      if (search) params.search = search;
      if (filter === 'own') params.is_own = true;
      if (filter === 'competitors') params.is_own = false;

      const res = await api.getProducts(params);
      setProducts(res.products);
      setTotal(res.total);
    } catch (error) {
      console.error('Failed to fetch products:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [filter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProducts();
  };

  const columns = [
    {
      key: 'name',
      header: 'Product Name',
      render: (product: Product) => (
        <div className="flex items-center">
          <Package className="mr-3 h-5 w-5 text-gray-400" />
          <div>
            <p className="font-medium text-gray-900">{product.name}</p>
            <p className="text-sm text-gray-500">{product.brand}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'sku',
      header: 'SKU',
    },
    {
      key: 'category',
      header: 'Category',
      render: (product: Product) => product.category || '-',
    },
    {
      key: 'is_own',
      header: 'Type',
      render: (product: Product) => (
        <span
          className={`rounded-full px-2 py-1 text-xs font-medium ${
            product.is_own
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-700'
          }`}
        >
          {product.is_own ? 'Own' : 'Competitor'}
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
            <h1 className="text-2xl font-bold text-gray-900">Products</h1>
            <p className="text-gray-500">
              Manage and monitor your products ({total} total)
            </p>
          </div>

          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <form onSubmit={handleSearch} className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search products..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-64 rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>
              <Button type="submit" variant="secondary" icon={Search}>
                Search
              </Button>
            </form>

            <div className="flex gap-2">
              <Button
                variant={filter === 'all' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setFilter('all')}
              >
                All
              </Button>
              <Button
                variant={filter === 'own' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setFilter('own')}
              >
                Own Products
              </Button>
              <Button
                variant={filter === 'competitors' ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setFilter('competitors')}
              >
                Competitors
              </Button>
            </div>
          </div>

          <div className="rounded-xl bg-white shadow-sm border border-gray-100">
            <DataTable
              columns={columns}
              data={products}
              keyExtractor={(p) => p.id}
              onRowClick={(p) => router.push(`/products/${p.id}`)}
              isLoading={isLoading}
              emptyMessage="No products found"
            />
          </div>
        </div>
      </main>
    </div>
  );
}
