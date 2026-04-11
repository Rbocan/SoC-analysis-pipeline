# SoC Manufacturing Data Analysis Dashboard

A FAANG-level, production-ready SoC validation dashboard with real-time analytics, multi-product support, and automated reporting.

## Architecture

```
React 19 + Next.js 15 (Frontend)
    ↕ REST API
FastAPI + Python (Backend)
    ↕
Polars + DuckDB + PostgreSQL + Redis
```

## Quick Start

### Prerequisites
- Docker + Docker Compose
- (Optional) Node 22 + Python 3.12 for local dev without Docker

### 1. Start infrastructure

```bash
docker-compose up -d postgres redis
```

### 2. Seed the database and generate synthetic data

```bash
docker-compose up -d backend
docker exec soc-analysis-pipeline-backend-1 python -m app.seed
```

This creates the `admin` user and generates 100k synthetic measurements per product.

### 3. Start all services

```bash
docker-compose up
```

Open:
- **Dashboard**: http://localhost:3000
- **API docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

Default credentials are set during the seed step (`app.seed`).

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # edit DATABASE_URL, REDIS_URL

uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan
│   │   ├── settings.py          # Pydantic settings
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── api/                 # Route handlers
│   │   │   ├── auth.py          # JWT login/register
│   │   │   ├── data.py          # Query/pivot/export/trend
│   │   │   ├── ml.py            # Failure prediction/drift/yield forecast
│   │   │   ├── products.py      # Product CRUD
│   │   │   ├── reports.py       # Report generation
│   │   │   ├── synthetic.py     # Synthetic data
│   │   │   └── health.py        # Health check
│   │   ├── config/
│   │   │   ├── products.yaml    # Product specs (YAML-driven)
│   │   │   ├── pipelines.yaml   # Pipeline schedule configs
│   │   │   └── loader.py        # Hot-reloadable YAML loader
│   │   ├── services/
│   │   │   ├── data_processor.py       # Polars + DuckDB
│   │   │   ├── synthetic_generator.py  # Faker + NumPy
│   │   │   ├── report_generator.py     # Jinja2 + WeasyPrint
│   │   │   ├── email_service.py        # aiosmtplib
│   │   │   ├── cache_service.py        # Redis
│   │   │   ├── scheduler.py            # APScheduler
│   │   │   └── auth_service.py         # JWT + bcrypt
│   │   ├── models/
│   │   │   ├── database.py      # SQLAlchemy ORM models
│   │   │   └── schemas.py       # Pydantic request/response
│   │   ├── middleware/
│   │   │   ├── audit.py         # Request audit logging
│   │   │   └── error_handler.py # Global exception handling
│   │   ├── templates/
│   │   │   └── daily_validation.html
│   │   ├── tests/
│   │   │   ├── test_auth.py
│   │   │   ├── test_data_processor.py
│   │   │   ├── test_synthetic_generator.py
│   │   │   └── test_config_loader.py
│   │   └── seed.py              # Bootstrap script
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── next.config.mjs          # Next.js config + CSP/security headers
│   └── src/
│       ├── app/                 # Next.js App Router pages
│       │   ├── dashboard/       # KPIs + trend charts
│       │   ├── explorer/        # TanStack Table + filters
│       │   ├── pivot/           # Pivot + heatmap
│       │   ├── reports/         # Generate + download reports
│       │   ├── products/        # Product config + data gen
│       │   ├── admin/           # Health + config management
│       │   └── login/           # Auth page
│       ├── components/
│       │   ├── layout/          # Sidebar, TopBar, AppShell
│       │   ├── charts/          # TrendChart, PassFailChart, HeatmapChart
│       │   └── ui/              # MetricCard, Badge, Spinner
│       ├── hooks/               # useData, useAuth
│       ├── store/               # Zustand (auth, filters)
│       └── lib/                 # api.ts, types.ts, utils.ts
│
└── docker-compose.yml
```

---

## Adding a New Product

Edit `backend/app/config/products.yaml`:

```yaml
products:
  - id: your_new_soc
    name: "Your SoC Name"
    description: "Brief description"
    data_source: "/data/parquet/your_new_soc.parquet"
    metrics:
      - name: voltage
        unit: "V"
        min_val: 0.9
        max_val: 1.2
        nominal: 1.05
        distribution: normal
    tests:
      - boot_test
      - stress_test
```

Then hit `POST /api/products/reload` (admin) or restart the backend. No code changes needed.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | JWT login |
| GET | `/api/products/` | List products |
| POST | `/api/data/query` | Query measurements |
| GET | `/api/data/metrics` | KPI summary |
| POST | `/api/data/pivot` | Pivot table |
| GET | `/api/data/trend` | Time-series trend |
| GET | `/api/data/export` | Export CSV/Parquet |
| POST | `/api/synthetic/generate` | Generate synthetic data |
| POST | `/api/reports/generate` | Generate HTML/PDF report |
| GET | `/api/reports/history` | Report history |
| POST | `/api/ml/train/{product_id}` | Train classifier + yield predictor |
| POST | `/api/ml/predict-failure/{product_id}` | Predict pass/fail |
| GET | `/api/ml/feature-importance/{product_id}` | Feature importances |
| GET | `/api/ml/yield-forecast/{product_id}` | Yield forecast |
| GET | `/api/ml/drift-status/{product_id}` | KS-test drift detection |
| GET | `/api/health/` | Health check |

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

---

## Performance Targets

| Operation | Target | Implementation |
|-----------|--------|----------------|
| Dashboard load | < 2s | React Query cache + Redis |
| Query (1M rows) | < 1s | Polars lazy evaluation |
| Pivot (10M rows) | < 5s | Polars + DuckDB fallback |
| Chart render | < 500ms | Recharts + memoization |

---

## Technology Stack

**Backend:** FastAPI · Polars · DuckDB · PostgreSQL · Redis · APScheduler · Jinja2 · WeasyPrint · JWT  
**Frontend:** Next.js 15 · React 19 · TypeScript · Tailwind CSS · Recharts · TanStack Table · TanStack Query · Zustand

---

## Implementation Phases

- [x] Phase 1: MVP — FastAPI + Polars + React dashboard
- [x] Phase 2: Core — YAML config, pivot tables, synthetic data, HTML reports
- [ ] Phase 3: Advanced — OAuth2 RBAC, Redis caching, virtual scrolling
- [ ] Phase 4: Production — Kubernetes, Prometheus, ELK, CI/CD
