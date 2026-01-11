# Railway Backend Deployment Guide

## Architecture

```
Browser → Vercel (Next.js) → Railway (Django)
          /api/v1/*         → RAILWAY_URL/api/v1/*
```

The Railway backend serves:
- `/api/v1/*` - REST API (JSON responses)
- `/admin/` - Django admin interface
- `/health/` - Infrastructure health checks

## Required Environment Variables

### Essential (Required for operation)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/dbname` |
| `DJANGO_SECRET_KEY` | Django secret key (generate unique) | `openssl rand -base64 50` |
| `DJANGO_DEBUG` | Debug mode (set to `false`) | `false` |
| `DJANGO_ALLOWED_HOSTS` | Allowed host headers | `web-production-9f63.up.railway.app,localhost` |

### Security (Required for production)

| Variable | Description | Example |
|----------|-------------|---------|
| `CORS_ALLOWED_ORIGINS` | Origins allowed for CORS | `https://olivas-retail-monitor.vercel.app,https://web-production-9f63.up.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | Origins trusted for CSRF | `https://olivas-retail-monitor.vercel.app,https://web-production-9f63.up.railway.app` |
| `FRONTEND_URL` | Frontend URL for redirects | `https://olivas-retail-monitor.vercel.app` |

### Background Tasks (Required for scraping)

| Variable | Description | Example |
|----------|-------------|---------|
| `CELERY_BROKER_URL` | Redis URL for Celery broker | `redis://default:xxx@host:6379` |
| `CELERY_RESULT_BACKEND` | Redis URL for Celery results | `redis://default:xxx@host:6379` |
| `REDIS_URL` | Redis URL for caching | `redis://default:xxx@host:6379` |

### Optional Features

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for review analysis | (disabled) |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot for alerts | (disabled) |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | (disabled) |
| `SENTRY_DSN` | Sentry error tracking DSN | (disabled) |

### Object Storage (Optional, for artifacts)

| Variable | Description | Default |
|----------|-------------|---------|
| `ARTIFACT_STORAGE_BACKEND` | Storage backend: `local`, `s3`, `r2` | `local` |
| `ARTIFACT_S3_ENDPOINT` | S3/R2 endpoint URL | |
| `ARTIFACT_S3_BUCKET` | S3/R2 bucket name | `retail-monitor-artifacts` |
| `ARTIFACT_S3_ACCESS_KEY` | S3/R2 access key | |
| `ARTIFACT_S3_SECRET_KEY` | S3/R2 secret key | |

### Admin Security (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_IP_ALLOWLIST` | IP addresses allowed to access /admin/ | (all allowed) |
| `ALLOW_BOOTSTRAP_ADMIN` | Enable admin bootstrap command | `false` |
| `ADMIN_EMAIL` | Bootstrap admin email | |
| `ADMIN_PASSWORD` | Bootstrap admin password (min 12 chars) | |

## Production Configuration Checklist

1. **Database**: Set `DATABASE_URL` to your PostgreSQL instance

2. **Security Keys**:
   ```bash
   # Generate a secure secret key
   openssl rand -base64 50
   ```
   Set as `DJANGO_SECRET_KEY`

3. **Hosts & Origins**:
   ```
   DJANGO_ALLOWED_HOSTS=web-production-9f63.up.railway.app,localhost
   CORS_ALLOWED_ORIGINS=https://olivas-retail-monitor.vercel.app,https://web-production-9f63.up.railway.app
   CSRF_TRUSTED_ORIGINS=https://olivas-retail-monitor.vercel.app,https://web-production-9f63.up.railway.app
   ```

4. **Debug**: Set `DJANGO_DEBUG=false`

5. **Frontend URL**: Set `FRONTEND_URL=https://olivas-retail-monitor.vercel.app`

## Health Check Endpoints

### `/api/v1/health/`

Primary health check for the API.

```bash
curl https://web-production-9f63.up.railway.app/api/v1/health/
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "ok",
  "timestamp": "2026-01-11T13:14:58.522377+00:00"
}
```

**Status codes:**
- `200` - Healthy
- `503` - Unhealthy (database connection issue)

### `/health/` (Infrastructure)

Used by Railway for deployment health checks.

## CSRF Handling

The API uses session-based authentication with CSRF protection.

**Endpoints exempt from CSRF** (using `@csrf_exempt`):
- `POST /api/v1/auth/login/` - Login
- `POST /api/v1/imports/create/` - Create imports
- `POST /api/v1/groups/create/` - Create monitoring groups
- `POST /api/v1/runs/` - Create runs
- `POST /api/v1/runs/{id}/retry/` - Retry failed runs
- `POST /api/v1/setup/retailers/` - Initialize retailers

All exempt endpoints **require authentication** (return 401 if not logged in).

**Endpoints requiring CSRF token:**
- `POST /api/v1/auth/logout/`
- `POST /api/v1/scrape/`

For frontend integration:
1. Call `GET /api/v1/auth/csrf/` to get CSRF token in cookie
2. Include `X-CSRFToken` header in POST requests

## Session Cookies

In production, session cookies are configured for cross-site usage:
- `SESSION_COOKIE_SECURE = True` (HTTPS only)
- `SESSION_COOKIE_SAMESITE = 'None'` (allows cross-origin with credentials)
- `CSRF_COOKIE_SAMESITE = 'None'`

This enables the Vercel frontend to maintain sessions with the Railway backend.

## Proxy Headers

Railway uses an edge proxy. Django is configured to trust:
- `X-Forwarded-Proto` for HTTPS detection (`SECURE_PROXY_SSL_HEADER`)
- `X-Forwarded-Host` for host detection (`USE_X_FORWARDED_HOST`)

## Troubleshooting

### CORS Errors

If you see CORS errors:
1. Check `CORS_ALLOWED_ORIGINS` includes your frontend URL (with `https://`)
2. Ensure `CORS_ALLOW_CREDENTIALS = True` is set (default)

### CSRF Errors

If POST requests fail with CSRF errors:
1. Use exempt endpoints (listed above) for API calls
2. Or obtain CSRF token via `/api/v1/auth/csrf/`

### 403 Forbidden on Admin

If `/admin/` returns 403:
1. Check `ADMIN_IP_ALLOWLIST` - empty means all IPs allowed
2. If set, add your IP or a range like `0.0.0.0/0`

### Database Connection Issues

If health check shows `database: error`:
1. Verify `DATABASE_URL` is correct
2. Check PostgreSQL is running and accessible
3. Check firewall/network rules

## Rollback Plan

Railway keeps deployment history. To rollback:

1. Go to Railway dashboard → Deployments
2. Find the last working deployment
3. Click "Redeploy" on that version

Or via CLI:
```bash
railway rollback
```
