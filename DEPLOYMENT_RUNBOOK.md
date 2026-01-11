# Retail Monitor Deployment Runbook

Complete step-by-step guide for deploying and verifying the Retail Monitor application.

## Architecture Overview

```
Browser → Vercel (Next.js Frontend) → Railway (Django Backend)
          olivas-retail-monitor.vercel.app    web-production-9f63.up.railway.app

          /api/v1/* → proxy → /api/v1/*
          /smoke    → client-side fetch
          /settings → client-side fetch
```

---

## Part 1: Vercel Configuration

### 1.1 Project Settings

1. Go to: https://vercel.com/dashboard
2. Select project: `olivas-retail-monitor` (or your project name)
3. Click **Settings** → **General**

**Verify these settings:**

| Setting | Required Value |
|---------|---------------|
| **Root Directory** | `frontend` |
| **Framework Preset** | Next.js |
| **Node.js Version** | 18.x or 20.x |
| **Build Command** | `npm run build` (default) |
| **Output Directory** | `.next` (default) |
| **Install Command** | `npm install` (default) |

### 1.2 Environment Variables

Go to: **Settings** → **Environment Variables**

**Required variables (set for BOTH Production AND Preview):**

| Variable | Value | Environments |
|----------|-------|--------------|
| `NEXT_PUBLIC_API_URL` | `https://web-production-9f63.up.railway.app` | Production, Preview |

**How to set:**
1. Click "Add New"
2. Enter variable name: `NEXT_PUBLIC_API_URL`
3. Enter value: `https://web-production-9f63.up.railway.app`
4. Check BOTH: ☑ Production ☑ Preview
5. Click "Save"

### 1.3 Redeploy Steps

**To redeploy after git push:**
```bash
# Automatic: Push triggers deploy
git push origin main
```

**To force redeploy from dashboard:**
1. Go to **Deployments** tab
2. Find latest deployment
3. Click **⋮** (three dots) → **Redeploy**
4. Select "Use existing Build Cache" = OFF for clean build
5. Click **Redeploy**

**To view deployment logs:**
1. Click on the deployment
2. Click "Building" or "Ready" status
3. View **Build Logs** tab for build output
4. View **Functions** tab for runtime errors

### 1.4 Verify Vercel Deployment

After deployment completes:

```bash
# 1. Check site loads
curl -I https://olivas-retail-monitor.vercel.app/

# Expected: HTTP 200

# 2. Check proxy route exists
curl -I https://olivas-retail-monitor.vercel.app/api/v1/health/

# Expected: HTTP 200 with JSON response

# 3. Check /smoke page
open https://olivas-retail-monitor.vercel.app/smoke/
```

---

## Part 2: Railway Configuration

### 2.1 Services Overview

Railway should have these services:
- **web** - Django web server (Gunicorn)
- **worker** - Celery worker for background tasks
- **beat** - Celery beat for scheduled tasks
- **PostgreSQL** - Database
- **Redis** - Cache and message broker

### 2.2 Required Environment Variables

Go to Railway Dashboard → Select your project → Click each service

**For ALL services (web, worker, beat):**

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |
| `DJANGO_SECRET_KEY` | Unique secret key | Generate with `openssl rand -base64 50` |
| `DJANGO_DEBUG` | Must be `false` | `false` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts | `web-production-9f63.up.railway.app,localhost` |
| `CORS_ALLOWED_ORIGINS` | CORS origins | `https://olivas-retail-monitor.vercel.app,https://web-production-9f63.up.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | CSRF origins | `https://olivas-retail-monitor.vercel.app,https://web-production-9f63.up.railway.app` |
| `FRONTEND_URL` | Frontend URL | `https://olivas-retail-monitor.vercel.app` |
| `CELERY_BROKER_URL` | Redis URL | `redis://default:xxx@host:6379` |
| `CELERY_RESULT_BACKEND` | Redis URL | `redis://default:xxx@host:6379` |
| `REDIS_URL` | Redis URL | `redis://default:xxx@host:6379` |

**Optional but recommended:**

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | For review analysis | (disabled) |
| `TELEGRAM_BOT_TOKEN` | For alerts | (disabled) |
| `TELEGRAM_CHAT_ID` | For alerts | (disabled) |
| `SENTRY_DSN` | Error tracking | (disabled) |
| `TZ` | Timezone | `Europe/Moscow` |

### 2.3 Verify Railway is Running

```bash
# 1. Check health endpoint directly
curl https://web-production-9f63.up.railway.app/api/v1/health/

# Expected response:
# {"status": "healthy", "database": "ok", "timestamp": "..."}

# 2. Check CSRF token endpoint
curl https://web-production-9f63.up.railway.app/api/v1/auth/csrf/

# Expected: HTTP 200 with Set-Cookie header

# 3. Check authentication required
curl -X POST https://web-production-9f63.up.railway.app/api/v1/imports/create/

# Expected: HTTP 401 (not 403 - confirms CSRF exemption works)
```

### 2.4 Railway Redeploy

**From Dashboard:**
1. Go to Railway Dashboard
2. Select your project
3. Click on the `web` service
4. Click **Deployments** tab
5. Click **Redeploy** on latest deployment

**Or trigger via git:**
```bash
git push origin main
# Railway auto-deploys on push if connected to repo
```

---

## Part 3: Verification Checklist

### 3.1 Visit /smoke Page

1. Open: https://olivas-retail-monitor.vercel.app/smoke/
2. Verify you see:
   - Green "Backend API: Connected" indicator
   - Response time displayed
   - "Database: healthy" status
   - No configuration error banner

**Expected output:**
```
System Health Status
━━━━━━━━━━━━━━━━━━━━

Backend API: Connected ✓
Response time: ~XXms

API Response:
{
  "status": "healthy",
  "database": "ok",
  "timestamp": "2026-01-11T..."
}
```

### 3.2 Test Product Import

1. Open: https://olivas-retail-monitor.vercel.app/import/
2. Paste a test URL:
   ```
   https://www.ozon.ru/product/123456789
   ```
3. Select "Competitor Products"
4. Click "Import 1 URL(s)"
5. Verify:
   - No CORS errors in browser console
   - Redirects to import detail page
   - Shows "processing" status
   - Eventually shows "completed" or "failed" with details

**If error occurs:**
- Check browser console (F12) for network errors
- Check if error card shows endpoint and status code
- Verify `/smoke` page still works

### 3.3 Test Scraping Session (Optional)

1. Open: https://olivas-retail-monitor.vercel.app/scraping/
2. Select a retailer (or "All Retailers")
3. Click "Start Scraping"
4. Verify:
   - Message shows "Scraping session started"
   - Session status card appears
   - Progress updates (if background tasks running)

**Note:** Requires Celery worker to be running on Railway.

---

## Part 4: Rollback Plan

### 4.1 Identify the Problem

**Frontend issue (Vercel)?**
- Site doesn't load at all
- JavaScript errors in console
- Blank page or "Application error"

**Backend issue (Railway)?**
- `/smoke` shows "Backend unreachable"
- API calls return 502/503
- Health check fails

### 4.2 Rollback Vercel

**Option A: Revert to Previous Deployment**
1. Go to Vercel Dashboard → Deployments
2. Find the last working deployment (green checkmark)
3. Click **⋮** → **Promote to Production**

**Option B: Revert Git Commit**
```bash
# Find last working commit
git log --oneline -10

# Revert to specific commit
git revert HEAD  # or specific commit hash

# Push revert
git push origin main
```

### 4.3 Rollback Railway

**Option A: Use Railway Dashboard**
1. Go to Railway Dashboard → Deployments
2. Find last working deployment
3. Click **Redeploy** on that version

**Option B: Railway CLI**
```bash
railway rollback
```

### 4.4 Restore Environment Variables

If you changed env vars and need to restore:

**Vercel:**
1. Go to Settings → Environment Variables
2. Click on variable → Edit
3. Restore previous value

**Railway:**
1. Click on service → Variables tab
2. Edit variable value
3. Service auto-restarts

---

## Part 5: Common Issues & Fixes

### Issue: "Load failed" on Dashboard

**Cause:** API proxy not reaching backend

**Fix:**
1. Check `/smoke` page - is backend reachable?
2. Verify `NEXT_PUBLIC_API_URL` is set in Vercel
3. Check Railway logs for errors

### Issue: CORS Errors in Console

**Cause:** Missing CORS configuration

**Fix:**
1. Verify Railway `CORS_ALLOWED_ORIGINS` includes Vercel URL
2. Must include `https://` prefix
3. Redeploy Railway after change

### Issue: 403 CSRF Error on POST

**Cause:** CSRF protection blocking request

**Fix:**
1. Verify endpoint is CSRF-exempt (check code)
2. Or ensure frontend fetches CSRF token first
3. Check `CSRF_TRUSTED_ORIGINS` includes Vercel URL

### Issue: 502 Bad Gateway

**Cause:** Backend crashed or unreachable

**Fix:**
1. Check Railway logs for errors
2. Verify database is running
3. Check memory/CPU limits
4. Restart Railway service

### Issue: Redirect Loop (308/301)

**Cause:** Trailing slash mismatch

**Fix:**
1. Verify `next.config.js` has `trailingSlash: true`
2. Verify `skipTrailingSlashRedirect: true`
3. Redeploy Vercel

---

## Part 6: Quick Reference

### URLs

| Service | URL |
|---------|-----|
| Frontend (Vercel) | https://olivas-retail-monitor.vercel.app |
| Backend (Railway) | https://web-production-9f63.up.railway.app |
| Health Check | https://web-production-9f63.up.railway.app/api/v1/health/ |
| Admin Panel | https://web-production-9f63.up.railway.app/admin/ |
| Smoke Test | https://olivas-retail-monitor.vercel.app/smoke/ |

### Key Commands

```bash
# Test backend health
curl https://web-production-9f63.up.railway.app/api/v1/health/

# Test frontend proxy
curl https://olivas-retail-monitor.vercel.app/api/v1/health/

# Generate new secret key
openssl rand -base64 50

# View Railway logs
railway logs

# View git history
git log --oneline -10
```

### Files Modified in This Fix

```
frontend/
├── next.config.js          # Trailing slash fix
├── src/
│   ├── app/
│   │   ├── api/v1/[...path]/route.ts  # Proxy handler
│   │   ├── smoke/page.tsx   # Health check page
│   │   ├── settings/page.tsx # Settings page
│   │   ├── error.tsx        # Error boundary
│   │   └── global-error.tsx # Global error boundary
│   ├── components/
│   │   └── ApiErrorCard.tsx # Diagnostic error display
│   └── lib/
│       └── api.ts           # API client with getApiBase()

src/config/settings.py       # SECURE_PROXY_SSL_HEADER added
```

---

## Deployment Checklist

Before deploying, verify:

- [ ] Code pushed to `main` branch
- [ ] Local build passes: `npm run build` in `/frontend`
- [ ] Vercel `NEXT_PUBLIC_API_URL` is set for Production + Preview
- [ ] Railway env vars are correct for all services
- [ ] Railway services are healthy (green status)

After deploying, verify:

- [ ] https://olivas-retail-monitor.vercel.app loads
- [ ] https://olivas-retail-monitor.vercel.app/smoke/ shows "healthy"
- [ ] Test import works without CORS errors
- [ ] No errors in browser console
- [ ] No errors in Railway logs
