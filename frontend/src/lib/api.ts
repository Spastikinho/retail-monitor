const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

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
    credentials: 'include',
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
};

export { ApiError };
