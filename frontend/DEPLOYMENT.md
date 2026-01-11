# Frontend Deployment Guide

## Architecture

```
Browser → Vercel (Next.js) → Railway (Django)
          /api/v1/*         → NEXT_PUBLIC_API_URL/api/v1/*
```

All browser API requests go through the Next.js proxy route at `/api/v1/[...path]/route.ts`.
This ensures same-origin requests with no CORS issues.

## Vercel Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Railway backend URL | `https://web-production-9f63.up.railway.app` |

### Optional (Auto-set by Vercel)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_VERCEL_ENV` | Deployment environment (`production`, `preview`, `development`) |
| `NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA` | Git commit SHA |

## Setup Instructions

### 1. Vercel Project Settings

1. Go to your Vercel project → Settings → Environment Variables
2. Add `NEXT_PUBLIC_API_URL`:
   - **Production**: `https://web-production-9f63.up.railway.app` (your Railway URL)
   - **Preview**: Same as production (or a staging backend if you have one)
   - **Development**: `http://localhost:8000`

### 2. Verify Deployment

After deploying, visit these pages to verify:

1. `/smoke/` - System health check (shows all services status)
2. `/settings/` - Configuration details and backend test button
3. `/api/v1/health/` - Raw backend health response

### 3. Troubleshooting

#### "Configuration Error" on /smoke

The frontend cannot reach the backend. Check:

1. `NEXT_PUBLIC_API_URL` is set correctly in Vercel
2. Railway backend is running and healthy
3. Backend URL doesn't have a trailing slash

#### Redirect Loop (infinite loading)

Fixed in this version. The issue was:
- Next.js default `trailingSlash: false` redirects `/api/v1/health/` → `/api/v1/health`
- Django's `APPEND_SLASH = True` redirects `/api/v1/health` → `/api/v1/health/`
- Result: Infinite 301/308 redirect loop

Solution:
- Set `trailingSlash: true` in `next.config.js`
- Proxy route normalizes all paths to include trailing slash

#### CORS Errors

Should not happen with the proxy architecture. If you see CORS errors:

1. Ensure you're not making direct calls to the backend URL from browser code
2. All API calls should go through `/api/v1/*` (relative path)
3. Check that `getApiBase()` returns empty string for browser requests

## Local Development

```bash
cd frontend

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Install and run
npm install
npm run dev
```

The dev server will proxy API requests to your local Django backend.

## API Client Usage

All API calls should use the `api` object from `@/lib/api`:

```typescript
import { api, checkBackendHealth, getApiConfig } from '@/lib/api';

// Data fetching
const summary = await api.getAnalyticsSummary();
const products = await api.getProducts({ limit: 10 });

// Health check with diagnostics
const health = await checkBackendHealth();
if (health.configurationError) {
  console.error('Backend not reachable:', health.error);
}

// Get configuration info
const config = getApiConfig();
console.log('API mode:', config.mode);  // 'proxy' in browser, 'direct' on server
console.log('Backend URL:', config.backendUrl);
```

## Rollback Plan

If deployment causes issues:

1. **Vercel**: Go to Deployments → Find last working deployment → Click "..." → "Promote to Production"
2. **Railway**: Railway automatically keeps deployment history. Redeploy previous version from dashboard.

To revert code changes:
```bash
git revert HEAD  # Revert last commit
git push         # Trigger new Vercel deployment
```
