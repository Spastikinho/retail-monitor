/**
 * Runs API Client - TypeScript types and methods for batch scraping
 *
 * API Contract:
 * - POST /api/v1/runs/create/ - Create a new scraping run
 * - GET /api/v1/runs/{run_id}/ - Get run status and results
 * - GET /api/v1/runs/ - List recent runs
 */

// ============================================================================
// Types
// ============================================================================

export interface RunItem {
  url: string;
  retailer?: string;
  name?: string;
}

export interface RunOptions {
  product_type?: 'own' | 'competitor';
  group_id?: string;
  scrape_reviews?: boolean;
}

export interface CreateRunRequest {
  items: RunItem[];
  options?: RunOptions;
}

export interface CreateRunResponse {
  success: boolean;
  run_id: string;
  created_at: string;
  items_count: number;
  errors?: Array<{ url: string; error: string }>;
}

export interface RunProgress {
  total: number;
  completed: number;
  failed: number;
  processing: number;
  percent: number;
}

export interface RunPriceData {
  regular: number | null;
  promo: number | null;
  final: number | null;
  change: number | null;
  change_pct: number | null;
}

export interface RunReviewsSummary {
  positive: number;
  negative: number;
  neutral: number;
}

export interface RunResult {
  id: string;
  url: string;
  retailer: string | null;
  product_title: string;
  custom_name: string;
  price: RunPriceData;
  rating: number | null;
  reviews_count: number | null;
  in_stock: boolean | null;
  reviews_summary: RunReviewsSummary | null;
  processed_at: string | null;
}

export interface RunError {
  id: string;
  url: string;
  error: string;
}

export interface RunInfo {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'completed_with_errors' | 'failed';
  created_at: string;
  finished_at: string | null;
  progress: RunProgress;
}

export interface GetRunResponse {
  success: boolean;
  run: RunInfo;
  results: RunResult[];
  errors: RunError[];
}

export interface RunSummary {
  id: string;
  status: string;
  items_total: number;
  items_completed: number;
  items_failed: number;
  created_at: string;
  finished_at: string | null;
}

export interface ListRunsResponse {
  success: boolean;
  total: number;
  runs: RunSummary[];
}

// ============================================================================
// API Base
// ============================================================================

const getApiBase = (): string => {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  if (process.env.NODE_ENV === 'production') {
    return '';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

export class RunsApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'RunsApiError';
  }
}

// ============================================================================
// API Methods
// ============================================================================

/**
 * Create a new scraping run with multiple URLs
 */
export async function createRun(request: CreateRunRequest): Promise<CreateRunResponse> {
  const apiBase = getApiBase();

  const response = await fetch(`${apiBase}/api/v1/runs/create/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(request),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new RunsApiError(data.error || 'Failed to create run', response.status);
  }

  return data;
}

/**
 * Get run status and results
 */
export async function getRun(runId: string): Promise<GetRunResponse> {
  const apiBase = getApiBase();

  const response = await fetch(`${apiBase}/api/v1/runs/${runId}/`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });

  const data = await response.json();

  if (!response.ok) {
    throw new RunsApiError(data.error || 'Failed to get run', response.status);
  }

  return data;
}

/**
 * List recent runs
 */
export async function listRuns(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ListRunsResponse> {
  const apiBase = getApiBase();

  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.append('status', params.status);
  if (params?.limit) searchParams.append('limit', params.limit.toString());
  if (params?.offset) searchParams.append('offset', params.offset.toString());

  const queryString = searchParams.toString();
  const url = `${apiBase}/api/v1/runs/${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  });

  const data = await response.json();

  if (!response.ok) {
    throw new RunsApiError(data.error || 'Failed to list runs', response.status);
  }

  return data;
}

/**
 * Poll a run until it completes
 */
export async function pollRunUntilComplete(
  runId: string,
  options?: {
    interval?: number; // ms between polls (default 2000)
    timeout?: number; // max time to wait in ms (default 300000 = 5 min)
    onProgress?: (run: GetRunResponse) => void;
  }
): Promise<GetRunResponse> {
  const interval = options?.interval ?? 2000;
  const timeout = options?.timeout ?? 300000;
  const startTime = Date.now();

  while (true) {
    const response = await getRun(runId);

    if (options?.onProgress) {
      options.onProgress(response);
    }

    const status = response.run.status;
    if (status === 'completed' || status === 'completed_with_errors' || status === 'failed') {
      return response;
    }

    if (Date.now() - startTime > timeout) {
      throw new RunsApiError('Polling timeout exceeded', 408);
    }

    await new Promise(resolve => setTimeout(resolve, interval));
  }
}

// ============================================================================
// Example Usage
// ============================================================================

/*
// Create a run with 3 URLs
const run = await createRun({
  items: [
    { url: 'https://www.ozon.ru/product/123' },
    { url: 'https://www.wildberries.ru/catalog/456/detail.aspx' },
    { url: 'https://vkusvill.ru/goods/some-product-789.html' },
  ],
  options: {
    product_type: 'competitor',
    scrape_reviews: true,
  },
});

console.log('Run created:', run.run_id);

// Poll until complete
const result = await pollRunUntilComplete(run.run_id, {
  onProgress: (r) => console.log(`Progress: ${r.run.progress.percent}%`),
});

console.log('Results:', result.results);
console.log('Errors:', result.errors);
*/
