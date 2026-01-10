const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-9f63.up.railway.app';

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, ...fetchOptions } = options;

  let url = `${API_URL}/api/v1${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new ApiError(error.error || 'Request failed', response.status);
  }

  return response.json();
}

// Types
export interface Product {
  id: string;
  name: string;
  brand: string;
  sku: string;
  is_own: boolean;
  category: string | null;
  created_at: string;
}

export interface ProductDetail extends Product {
  barcode: string;
  description: string;
  listings: Listing[];
}

export interface Listing {
  id: string;
  retailer: string;
  external_url: string;
  last_scraped: string | null;
  latest_price: {
    price_final: number;
    price_regular: number;
    in_stock: boolean;
    rating_avg: number | null;
    reviews_count: number | null;
    scraped_at: string;
  } | null;
}

export interface Retailer {
  id: string;
  name: string;
  code: string;
  website: string;
}

export interface PriceHistory {
  date: string;
  price_final: number;
  price_regular: number;
  price_promo: number | null;
  in_stock: boolean;
  rating_avg: number | null;
  reviews_count: number | null;
}

export interface AlertEvent {
  id: string;
  rule_name: string;
  alert_type: string;
  product: string;
  retailer: string;
  message: string;
  details: Record<string, unknown>;
  triggered_at: string;
  is_delivered: boolean;
  delivered_at: string | null;
}

export interface AnalyticsSummary {
  products: {
    total: number;
    own: number;
    competitors: number;
  };
  listings: number;
  recent_activity: {
    snapshots_7d: number;
    reviews_7d: number;
    alerts_7d: number;
    sessions_7d: number;
  };
}

export interface HealthCheck {
  status: string;
  database: string;
  timestamp: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  authenticated?: boolean;
  error?: string;
}

export interface ManualImport {
  id: string;
  url: string;
  retailer: string | null;
  product_type: 'own' | 'competitor';
  product_title: string;
  custom_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  price_final: number | null;
  price_change: number | null;
  price_change_pct: number | null;
  rating: number | null;
  reviews_count: number | null;
  in_stock: boolean | null;
  reviews_positive: number;
  reviews_negative: number;
  monitoring_period: string | null;
  created_at: string;
  processed_at: string | null;
  error_message: string | null;
}

export interface ManualImportDetail extends ManualImport {
  notes: string;
  price_regular: number | null;
  price_promo: number | null;
  price_previous: number | null;
  reviews_neutral: number;
  review_insights: Record<string, unknown>;
  reviews_data: Array<{
    rating: number;
    text: string;
    author: string;
    date: string;
    pros?: string;
    cons?: string;
  }>;
  is_recurring: boolean;
  group: { id: string; name: string } | null;
}

export interface MonitoringGroup {
  id: string;
  name: string;
  description: string;
  group_type: 'own' | 'competitor';
  color: string;
  imports_count: number;
}

export interface MonitoringPeriod {
  period: string;
  label: string;
  count: number;
}

// API Methods
export const api = {
  // Health
  health: () => request<HealthCheck>('/health/'),

  // Authentication
  checkAuth: () => request<AuthResponse>('/auth/check/'),

  login: (username: string, password: string) =>
    request<AuthResponse>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  logout: () =>
    request<{ success: boolean }>('/auth/logout/', { method: 'POST' }),

  // Products
  getProducts: (params?: { is_own?: boolean; category?: string; brand?: string; search?: string; limit?: number; offset?: number }) =>
    request<{ success: boolean; total: number; products: Product[] }>('/products/', { params }),

  getProduct: (id: string) =>
    request<{ success: boolean; product: ProductDetail; listings: Listing[] }>(`/products/${id}/`),

  // Retailers
  getRetailers: () =>
    request<{ success: boolean; retailers: Retailer[] }>('/retailers/'),

  // Price History
  getPriceHistory: (listingId: string, days?: number) =>
    request<{ success: boolean; listing_id: string; product: string; retailer: string; history: PriceHistory[] }>(
      `/price-history/${listingId}/`,
      { params: { days } }
    ),

  // Alerts
  getAlerts: (params?: { days?: number; delivered?: boolean; limit?: number }) =>
    request<{ success: boolean; events: AlertEvent[] }>('/alerts/', { params }),

  // Analytics
  getAnalyticsSummary: () =>
    request<{ success: boolean; summary: AnalyticsSummary }>('/analytics/summary/'),

  // Scraping
  triggerScrape: (params?: { listing_id?: string; retailer_id?: string }) =>
    request<{ success: boolean; message: string; session_id?: string; listing_id?: string }>(
      '/scrape/',
      { method: 'POST', body: JSON.stringify(params || {}) }
    ),

  getScrapeStatus: (sessionId: string) =>
    request<{
      success: boolean;
      session: {
        id: string;
        status: string;
        trigger_type: string;
        retailer: string;
        listings_total: number;
        listings_success: number;
        listings_failed: number;
        started_at: string | null;
        finished_at: string | null;
        error_log: string | null;
      };
    }>(`/scrape/${sessionId}/status/`),

  // Export
  exportProducts: (params?: { is_own?: boolean }) =>
    request<{ success: boolean; exported_at: string; product_count: number; products: unknown[] }>(
      '/export/products/',
      { params }
    ),

  // Manual Import
  getImports: (params?: { status?: string; product_type?: string; period?: string; limit?: number; offset?: number }) =>
    request<{ success: boolean; total: number; imports: ManualImport[] }>('/imports/', { params }),

  getImport: (id: string) =>
    request<{ success: boolean; import: ManualImportDetail }>(`/imports/${id}/`),

  createImports: (data: { urls: string[]; product_type?: string; group_id?: string }) =>
    request<{ success: boolean; message: string; imports: Array<{ id: string; url: string; retailer: string | null; status: string }>; errors: string[] }>(
      '/imports/create/',
      { method: 'POST', body: JSON.stringify(data) }
    ),

  // Monitoring Groups
  getGroups: () =>
    request<{ success: boolean; groups: MonitoringGroup[] }>('/groups/'),

  createGroup: (data: { name: string; description?: string; group_type?: string; color?: string; id?: string }) =>
    request<{ success: boolean; group: MonitoringGroup }>(
      '/groups/create/',
      { method: 'POST', body: JSON.stringify(data) }
    ),

  // Periods
  getPeriods: () =>
    request<{ success: boolean; periods: MonitoringPeriod[] }>('/periods/'),

  // Excel Export URLs (for direct download)
  getExportMonitoringUrl: (period?: string) => {
    const base = `${API_URL}/api/v1/export/monitoring/`;
    return period ? `${base}?period=${period}` : base;
  },

  getExportImportUrl: (importId: string) =>
    `${API_URL}/api/v1/export/import/${importId}/`,
};

export { ApiError };
// Deploy trigger 1768057286
