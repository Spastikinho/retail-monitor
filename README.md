# Retail Monitor

Price monitoring and competitor analysis platform for Russian retail marketplaces.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                 │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    FRONTEND (Vercel)                             │   │
│  │                    Next.js + React + TypeScript                  │   │
│  │                    /frontend directory                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                         │
│                               │ API calls via Vercel rewrites           │
│                               │ (same-origin, no CORS)                  │
│                               ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BACKEND (Railway)                             │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐               │   │
│  │  │  Django    │  │   Celery   │  │   Celery   │               │   │
│  │  │  API/Admin │  │   Worker   │  │   Beat     │               │   │
│  │  └────────────┘  └────────────┘  └────────────┘               │   │
│  │         │               │                │                     │   │
│  │         └───────────────┴────────────────┘                     │   │
│  │                         │                                       │   │
│  │         ┌───────────────┴───────────────┐                      │   │
│  │         ▼                               ▼                      │   │
│  │  ┌─────────────┐                 ┌─────────────┐               │   │
│  │  │ PostgreSQL  │                 │    Redis    │               │   │
│  │  │  (Railway)  │                 │  (Railway)  │               │   │
│  │  └─────────────┘                 └─────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## UI Entry Point

**The Next.js frontend (`/frontend`) is the SINGLE source of UI truth.**

- **Production**: Frontend served by Vercel, API by Django/Railway
- **Django templates**: Deprecated for user-facing features; Admin panel (`/admin/`) remains for internal ops
- **Django `UI_MODE`**: Set to `api-only` in production (default), `django` for local development with templates

## Quick Start (Local Development)

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for frontend)

### Backend Setup

```bash
# Clone and enter directory
cd retail_monitor

# Create environment file
cp .env.example .env
# Edit .env with your secrets

# Start services
make build
make up
make init

# Backend runs at http://localhost:8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm ci

# Create local env
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

# Run development server
npm run dev

# Frontend runs at http://localhost:3000
```

## Deployment

### Vercel (Frontend)

**Settings:**
| Setting | Value |
|---------|-------|
| Root Directory | `frontend` |
| Framework Preset | Next.js |
| Build Command | `npm run build` |
| Install Command | `npm ci` |
| Output Directory | `.next` |
| Node.js Version | 20.x |

**Environment Variables:**
```
NEXT_PUBLIC_API_URL=https://your-railway-app.up.railway.app
```

**Local Build Test:**
```bash
cd frontend
npm ci
npm run build
# Verify: No errors, .next directory created
```

### Railway (Backend)

Deploy Django, Celery Worker, and Celery Beat as separate services sharing the same codebase.

**Environment Variables:**
```env
# Required
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
DJANGO_SECRET_KEY=<generate-secure-key>
DJANGO_ALLOWED_HOSTS=your-app.up.railway.app

# Frontend integration
FRONTEND_URL=https://your-vercel-app.vercel.app
UI_MODE=api-only
CORS_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-vercel-app.vercel.app

# Optional
TELEGRAM_BOT_TOKEN=<your-token>
TELEGRAM_CHAT_ID=<your-chat-id>
OPENAI_API_KEY=<your-key>
```

## Smoke Test

After deployment, verify:

1. **Frontend**: Visit `https://your-vercel-app.vercel.app/smoke`
   - Should show "Frontend: Deployed"
   - Should show "Backend: ok" (if backend is running)

2. **Backend API**: `curl https://your-railway-app.up.railway.app/api/v1/health/`
   - Should return `{"status": "ok", ...}`

3. **Admin**: Visit `https://your-railway-app.up.railway.app/admin/`
   - Should show Django admin login

## Supported Retailers

| Retailer | Prices | Reviews | Status |
|----------|--------|---------|--------|
| Ozon | ✓ | ✓ | Full support |
| Wildberries | ✓ | ✓ | Full support |
| VkusVill | ✓ | ✓ | Full support |
| Perekrestok | ✓ | ✓ | Full support |
| Yandex Lavka | ✓ | ✓ | Full support |

## Project Structure

```
retail_monitor/
├── frontend/              # Next.js frontend (Vercel)
│   ├── src/
│   │   ├── app/          # App Router pages
│   │   ├── components/   # React components
│   │   └── lib/          # API client, utilities
│   ├── vercel.json       # Vercel configuration
│   └── package.json
│
├── src/                   # Django backend (Railway)
│   ├── config/           # Django settings
│   ├── apps/
│   │   ├── api/          # REST API endpoints
│   │   ├── core/         # Health checks, base
│   │   ├── products/     # Product management
│   │   ├── retailers/    # Retailer configuration
│   │   ├── scraping/     # Connectors, Celery tasks
│   │   ├── alerts/       # Alert rules, notifications
│   │   └── reports/      # Export functionality
│   └── templates/        # Django templates (deprecated for UI)
│
├── data/                  # Local data (not for production)
│   ├── raw_snapshots/    # Use object storage in prod
│   ├── exports/          # Use object storage in prod
│   └── imports/          # Use object storage in prod
│
├── docker-compose.yml    # Local development
└── Makefile              # Development commands
```

## API Endpoints

Key API endpoints consumed by the frontend:

- `GET /api/v1/health/` - Health check
- `GET /api/v1/products/` - List products
- `GET /api/v1/retailers/` - List retailers
- `POST /api/v1/imports/create/` - Create URL imports
- `GET /api/v1/imports/` - List imports
- `GET /api/v1/analytics/summary/` - Dashboard stats
- `GET /api/v1/alerts/` - List alert events

See `frontend/src/lib/api.ts` for full API client.

## Development Commands

```bash
make up        # Start all services
make down      # Stop services
make logs      # View logs
make shell     # Django shell
make bash      # Bash in web container
make migrate   # Apply migrations
make test      # Run tests
make clean     # Remove containers and data
```

## License

Internal tool.
