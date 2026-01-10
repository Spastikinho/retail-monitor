'use client';

import { useEffect, useState } from 'react';
import { FolderPlus, Folder, Package, Users, Plus } from 'lucide-react';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/Button';
import { api, MonitoringGroup, ManualImport } from '@/lib/api';

export default function MonitoringPage() {
  const [groups, setGroups] = useState<MonitoringGroup[]>([]);
  const [imports, setImports] = useState<ManualImport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newGroup, setNewGroup] = useState({
    name: '',
    description: '',
    group_type: 'own' as 'own' | 'competitor',
    color: '#3B82F6',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [groupsRes, importsRes] = await Promise.all([
        api.getGroups(),
        api.getImports({ status: 'completed', limit: 100 }),
      ]);
      setGroups(groupsRes.groups);
      setImports(importsRes.imports);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroup.name.trim()) return;

    setIsSubmitting(true);
    try {
      await api.createGroup(newGroup);
      setNewGroup({ name: '', description: '', group_type: 'own', color: '#3B82F6' });
      setShowCreateForm(false);
      fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create group');
    } finally {
      setIsSubmitting(false);
    }
  };

  const ownProducts = imports.filter(i => i.product_type === 'own');
  const competitorProducts = imports.filter(i => i.product_type === 'competitor');

  const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />

      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Monitoring</h1>
              <p className="text-gray-500">Organize and track your product monitoring</p>
            </div>
            <Button icon={FolderPlus} onClick={() => setShowCreateForm(!showCreateForm)}>
              New Group
            </Button>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          {/* Create Group Form */}
          {showCreateForm && (
            <div className="mb-8 rounded-xl bg-white p-6 shadow-sm border border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Create Monitoring Group</h2>
              <form onSubmit={handleCreateGroup}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Group Name
                    </label>
                    <input
                      type="text"
                      value={newGroup.name}
                      onChange={(e) => setNewGroup({ ...newGroup, name: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      placeholder="e.g., Q1 2024 Olive Products"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Type
                    </label>
                    <select
                      value={newGroup.group_type}
                      onChange={(e) => setNewGroup({ ...newGroup, group_type: e.target.value as 'own' | 'competitor' })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="own">Our Products</option>
                      <option value="competitor">Competitor Products</option>
                    </select>
                  </div>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={newGroup.description}
                    onChange={(e) => setNewGroup({ ...newGroup, description: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    rows={2}
                    placeholder="Optional description..."
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Color
                  </label>
                  <div className="flex space-x-2">
                    {colors.map((color) => (
                      <button
                        key={color}
                        type="button"
                        onClick={() => setNewGroup({ ...newGroup, color })}
                        className={`w-8 h-8 rounded-full border-2 ${
                          newGroup.color === color ? 'border-gray-900' : 'border-transparent'
                        }`}
                        style={{ backgroundColor: color }}
                      />
                    ))}
                  </div>
                </div>
                <div className="flex space-x-2">
                  <Button type="submit" icon={Plus} isLoading={isSubmitting}>
                    Create Group
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => setShowCreateForm(false)}>
                    Cancel
                  </Button>
                </div>
              </form>
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
            </div>
          ) : (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <div className="flex items-center">
                    <div className="p-3 rounded-lg bg-green-100 mr-4">
                      <Package className="h-6 w-6 text-green-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-gray-900">{ownProducts.length}</p>
                      <p className="text-sm text-gray-500">Our Products</p>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <div className="flex items-center">
                    <div className="p-3 rounded-lg bg-yellow-100 mr-4">
                      <Users className="h-6 w-6 text-yellow-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-gray-900">{competitorProducts.length}</p>
                      <p className="text-sm text-gray-500">Competitor Products</p>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                  <div className="flex items-center">
                    <div className="p-3 rounded-lg bg-primary-100 mr-4">
                      <Folder className="h-6 w-6 text-primary-600" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-gray-900">{groups.length}</p>
                      <p className="text-sm text-gray-500">Monitoring Groups</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Groups List */}
              <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100 mb-8">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Monitoring Groups</h2>

                {groups.length === 0 ? (
                  <div className="text-center py-8">
                    <Folder className="h-12 w-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500">No groups yet</p>
                    <p className="text-sm text-gray-400">Create a group to organize your products</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {groups.map((group) => (
                      <div
                        key={group.id}
                        className="p-4 rounded-lg border border-gray-200 hover:border-primary-300 transition-colors"
                      >
                        <div className="flex items-center mb-2">
                          <div
                            className="w-4 h-4 rounded-full mr-3"
                            style={{ backgroundColor: group.color }}
                          />
                          <h3 className="font-medium text-gray-900">{group.name}</h3>
                        </div>
                        {group.description && (
                          <p className="text-sm text-gray-500 mb-2">{group.description}</p>
                        )}
                        <div className="flex items-center justify-between">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            group.group_type === 'own'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {group.group_type === 'own' ? 'Our' : 'Competitor'}
                          </span>
                          <span className="text-sm text-gray-500">
                            {group.imports_count} products
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Recent Activity */}
              <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Products</h2>

                {imports.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No products monitored yet</p>
                ) : (
                  <div className="space-y-3">
                    {imports.slice(0, 10).map((imp) => (
                      <div
                        key={imp.id}
                        className="flex items-center justify-between p-3 rounded-lg bg-gray-50"
                      >
                        <div className="flex-1 min-w-0 mr-4">
                          <p className="font-medium text-gray-900 truncate">
                            {imp.product_title || imp.custom_name || 'Processing...'}
                          </p>
                          <p className="text-sm text-gray-500">{imp.retailer}</p>
                        </div>
                        <div className="flex items-center space-x-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            imp.product_type === 'own'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {imp.product_type === 'own' ? 'Our' : 'Competitor'}
                          </span>
                          {imp.price_final && (
                            <span className="font-medium text-gray-900">
                              {imp.price_final.toFixed(2)} ₽
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
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
