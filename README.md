## PRISM AI – Conversational Business Intelligence for Sales Patterns

PRISM AI is a full-stack Business Intelligence application that lets business users explore sales patterns and forecasts through a conversational interface.  
It combines Databricks, advanced time‑series signal processing (STFT, wavelets, Hilbert–Huang Transform), and an LLM hosted via NVIDIA NIM to surface actionable insights.

### High‑Level Features

- **Conversational BI assistant**: Ask natural language questions about sales patterns, trends, spikes, dips, volatility, and seasonality.
- **Pattern mining on Databricks**: Reads precomputed pattern metadata and raw sales data from your Databricks Lakehouse.
- **Pattern‑aware forecasting**: Uses pattern‑based forecaster to generate future sales projections and an LLM to translate them into business language.
- **Transform pipeline orchestration**: Triggers a Databricks job to (re)compute pattern metadata or run a local transform pipeline for testing.
- **Caching layer**: Redis-backed cache to speed up repeated queries and forecasts.

---

## Architecture Overview

- **Backend**: FastAPI app (`src/api/main.py`) exposing:
  - `POST /api/query/chat` – conversational pattern analysis
  - `POST /api/query/chat/stream` – streaming LLM responses (SSE)
  - `GET /api/query/patterns` – filterable pattern catalog
  - `POST /api/forecast/generate` – pattern‑aware forecast with narrative
  - `GET /api/forecast/history/{product_id}` – historical forecasts
  - `POST /api/transform/run` – trigger Databricks job
  - `GET /api/transform/status/{run_id}` – job status
  - `POST /api/transform/run-local` – local feature extraction + pattern detection
- **Data layer**: `DatabricksService` (`src/api/services/databricks.py`) queries:
  - `pattern_metadata` – per‑product pattern features and confidence
  - `sales_daily_clean` – raw daily sales
  - `forecasts` – persisted forecasts (optional)
- **LLM layer**: `ClaudeService` (`src/api/services/claude.py`) wraps an NVIDIA NIM chat completion endpoint and:
  - summarizes detected patterns for `chat` endpoints
  - explains forecasts in business terms for `/api/forecast/generate`
- **Cache**: `CacheService` (`src/api/services/cache.py`) backed by Redis.
- **Frontend**: Next.js 14 app in `frontend/` with a single-page conversational UI (`ChatInterface.tsx`).

For a deeper architectural walk‑through, see `docs/ARCHITECTURE.md`.

---

## Prerequisites

- **Python**: 3.10+
- **Node.js**: 18+ (for Next.js 14)
- **Redis**: running instance (local or remote)
- **Databricks**:
  - Workspace with SQL warehouse
  - Tables: `prism_ai.sales.pattern_metadata`, `prism_ai.sales.sales_daily_clean`, and optionally `prism_ai.sales.forecasts`
- **LLM Endpoint (NVIDIA NIM)**:
  - Chat completion endpoint compatible with `POST /chat/completions`

---

## Backend Setup (FastAPI)

From the project root:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

Create a `.env` file in the project root (or update existing one) with:

```bash
# Databricks
DATABRICKS_HOST="https://<your-databricks-host>"
DATABRICKS_TOKEN="<your-token>"
DATABRICKS_WAREHOUSE_ID="<sql-warehouse-id>"
DATABRICKS_CATALOG="prism_ai"
DATABRICKS_SCHEMA="sales"
TRANSFORM_JOB_ID="<optional-job-id>"

# NVIDIA NIM (LLM)
NVIDIA_API_KEY="<your-nim-api-key>"
NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
NVIDIA_CHAT_MODEL="meta/llama-3.1-70b-instruct"

# Redis
REDIS_URL="redis://localhost:6379"
CACHE_TTL=3600

# Optional: general
ENV="development"
LOG_LEVEL="INFO"
```

The environment variable names map to the `Settings` fields in `src/config.py` (Pydantic will read from `.env`).

Run the API locally:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Once running, you can access:

- **Health check**: `GET http://localhost:8000/health`
- **Swagger docs**: `http://localhost:8000/docs`

---

## Frontend Setup (Next.js)

From the `frontend/` directory:

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL="http://localhost:8000"
```

Run the dev server:

```bash
npm run dev
```

Then open `http://localhost:3000` in your browser.

---

## Using the Conversational Interface

In the web UI you can:

- **Ask pattern questions**, e.g.:
  - “Show me products trending up”
  - “Find products with spikes in the last quarter”
  - “What products are highly volatile in jackets?”
- **Request forecasts**, e.g.:
  - “Forecast sales for Product_123 for the next 6 months”
  - “Predict seasonal demand for Summer Jacket for the next 3 months”
- **Trigger pipeline runs**, e.g.:
  - “Run the pattern analysis pipeline” (mapped to `/api/transform/run`)

The `ChatInterface` component will:

- Detect whether you are asking for a **query**, **forecast**, or **transform run**.
- Call the corresponding FastAPI endpoint.
- Render text responses from the LLM and, when applicable, display forecast charts inline.

---

## Key API Endpoints

- **Conversational Pattern Analysis**
  - `POST /api/query/chat`
    - Body: `{ "message": string, "filters"?: object }`
    - Returns: LLM‑generated insight plus pattern metadata count and applied filters.
  - `POST /api/query/chat/stream`
    - Same payload as `/chat`, but streams tokens using `text/event-stream`.
  - `GET /api/query/patterns`
    - Query params: `product_id`, `pattern_type`, `category`, `min_confidence`, `trend_direction`, `limit`.

- **Forecasting**
  - `POST /api/forecast/generate`
    - Body: `{ "product_id": string, "horizon"?: number }`
    - Returns: structured forecast (dates, values, intervals) and a business‑friendly explanation from the LLM.
  - `GET /api/forecast/history/{product_id}`
    - Returns persisted forecasts when present in Databricks.

- **Transform & Pattern Detection**
  - `POST /api/transform/run`
    - Body: `{ "start_date"?: string, "end_date"?: string, "product_ids"?: string[] }`
    - Returns Databricks job `run_id`.
  - `GET /api/transform/status/{run_id}`
    - Returns job lifecycle and result status.
  - `POST /api/transform/run-local`
    - Runs the transform pipeline and pattern classifier locally using a subset of data.

See `docs/API_REFERENCE.md` for example payloads and full details.

---

## Testing the System

- Use the built‑in **Swagger UI** at `http://localhost:8000/docs` to:
  - Call `/api/query/patterns` and verify your Databricks tables and filters are working.
  - Test `/api/forecast/generate` for a handful of products.
- Use the **web UI** to:
  - Try quick filters (“Trending up”, “Spikes”, “Volatile”) from the chips above the input box.
  - Ask free‑form questions about patterns and forecasts.

---

## Deployment Notes

- Backend can be deployed as a containerized FastAPI app (e.g., to Azure Container Apps, ECS, or Kubernetes) with:
  - Network access to Databricks and Redis.
  - Access to the NVIDIA NIM endpoint.
- Frontend can be deployed as a static Next.js app (e.g., Vercel, Netlify) configured with `NEXT_PUBLIC_API_URL` pointing to the backend API.

Ensure environment variables in production match the `Settings` model in `src/config.py`.

# prismAI
An end-to-end sales analytics platform with a novel pattern recognition core algorithm and easy-to-use conversational interface.
# PRISM AI
# 
# Sales pattern detection and forecasting with conversational AI interface.
# 
# ## Architecture
# 
# ```
# ┌─────────────────────────────────────────────────────────┐
# │  Chat Interface (Next.js)                               │
# └────────────────────┬────────────────────────────────────┘
#                      │
#                      ▼
# ┌─────────────────────────────────────────────────────────┐
# │  FastAPI Backend                                        │
# │  ├── /api/query    → Chat, pattern queries              │
# │  ├── /api/transform → Run pipeline on new data          │
# │  └── /api/forecast  → Generate predictions              │
# └────────────────────┬────────────────────────────────────┘
#                      │
#          ┌───────────┼───────────┐
#          ▼           ▼           ▼
# ┌─────────────┐ ┌─────────┐ ┌─────────────┐
# │ Databricks  │ │  Redis  │ │ Claude API  │
# │ Unity Cat.  │ │  Cache  │ │ Interpret   │
# └─────────────┘ └─────────┘ └─────────────┘
# ```
# 
# ## Quick Start
# 
# ```bash
# # Clone
# git clone https://github.com/yourusername/prism-ai.git
# cd prism-ai
# 
# # Setup environment
# cp .env.example .env
# # Edit .env with your credentials
# 
# # Run with Docker
# docker-compose up -d
# 
# # Or run locally
# python -m venv venv
# source venv/bin/activate
# pip install -e .
# uvicorn src.api.main:app --reload
# ```
# 
# ## API Endpoints
# 
# ### Query Mode
# - `POST /api/query/chat` - Chat with pattern data
# - `POST /api/query/chat/stream` - Streaming chat response
# - `GET /api/query/patterns` - List patterns with filters
# - `GET /api/query/patterns/{product_id}` - Get single product pattern
# 
# ### Transform Mode
# - `POST /api/transform/run` - Trigger Databricks pipeline
# - `GET /api/transform/status/{run_id}` - Check job status
# - `POST /api/transform/run-local` - Run locally (small data)
# 
# ### Forecast Mode
# - `POST /api/forecast/generate` - Generate forecast
# - `GET /api/forecast/history/{product_id}` - Get forecast history
# 
# ## Unity Catalog Tables
# 
# ```
# prism_ai.sales.raw_sales_daily
# prism_ai.sales.features_stft
# prism_ai.sales.features_wavelet
# prism_ai.sales.features_hht
# prism_ai.sales.features_combined
# prism_ai.sales.detected_patterns
# prism_ai.sales.final_patterns_validated
# prism_ai.sales.forecasts
# ```
# 
# ## Transform Pipeline
# 
# Three transforms extract features from sales time series:
# 
# 1. **STFT** - Frequency domain analysis, detects periodicity
# 2. **Wavelet (CWT)** - Multi-scale analysis, detects localized events
# 3. **HHT** - Adaptive decomposition, detects frequency drift
# 
# Pattern types detected:
# - `fixed_seasonality` - Consistent periodic pattern
# - `varying_seasonality` - Changing periodic pattern
# - `slow_trend` - Gradual increase/decrease
# - `sudden_spike` - Anomalous peak
# - `sudden_dip` - Anomalous drop
# - `stable_flat` - Minimal variation
# - `high_volatility` - Unpredictable fluctuation
# 
# ## Configuration
# 
# All settings via environment variables (no hardcoding):
# 
# | Variable | Description |
# |----------|-------------|
# | `DATABRICKS_HOST` | Workspace URL |
# | `DATABRICKS_TOKEN` | PAT token |
# | `DATABRICKS_WAREHOUSE_ID` | SQL Warehouse ID |
# | `DATABRICKS_CATALOG` | Unity Catalog name |
# | `DATABRICKS_SCHEMA` | Schema name |
# | `TRANSFORM_JOB_ID` | Databricks job ID |
# | `ANTHROPIC_API_KEY` | Claude API key |
# | `REDIS_URL` | Redis connection string |
# 
# ## Test Results
# 
# Transform outputs saved to `/tests` directory:
# - `transform_results_YYYYMMDD_HHMMSS.csv`
# 
# ## License
# 
# MIT