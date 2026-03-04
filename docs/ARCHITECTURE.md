## PRISM AI Architecture & Internals

This document provides a deeper look at how PRISM AI is structured so that you can extend or customize it for your own Business Intelligence use cases.

---

## 1. Backend Layout (FastAPI)

- `src/api/main.py`
  - Creates the FastAPI app, configures CORS, and mounts routers:
    - `src/api/routes/query.py` → conversational pattern analysis & pattern catalog
    - `src/api/routes/forecast.py` → forecasting endpoints
    - `src/api/routes/transform.py` → transform pipeline orchestration
  - Exposes:
    - `GET /` – basic status payload
    - `GET /health` – health check

- `src/api/dependencies.py`
  - Uses `functools.lru_cache` to lazily instantiate singletons:
    - `DatabricksService` – data access
    - `ClaudeService` – LLM wrapper
    - `CacheService` – Redis cache
  - This design avoids recreating heavy clients per request while staying FastAPI‑compatible.

---

## 2. Configuration (`src/config.py`)

The `Settings` class (Pydantic `BaseSettings`) is the single source of truth for configuration:

- **Databricks**
  - `databricks_host`, `databricks_token`, `databricks_warehouse_id`
  - `databricks_catalog`, `databricks_schema`
  - `transform_job_id` (for the remote transform job)
- **LLM / NVIDIA NIM**
  - `nvidia_api_key`, `nvidia_base_url`
  - `nvidia_chat_model` (used by `ClaudeService`)
- **Redis**
  - `redis_url`
  - `cache_ttl`
- **Signal processing parameters**
  - `stft_nperseg`, `wavelet_max_scale`, `hht_max_imfs`, etc.

All values can be set via environment variables or `.env` file; `get_settings()` caches a single `Settings` instance.

---

## 3. Data Access Layer (`DatabricksService`)

Located in `src/api/services/databricks.py`, this class encapsulates all interaction with Databricks:

- Uses `databricks-sql-connector` for SQL queries and `databricks-sdk` for job control.
- Helper:
  - `_table(name: str)` → returns fully‑qualified table name using catalog & schema.
- Core methods:
  - `query(sql_query: str) -> pd.DataFrame`
  - `execute(sql_query: str) -> None`
  - `get_patterns(filters: dict = None, limit: int = None) -> pd.DataFrame`
    - Builds a SQL query over `pattern_metadata` with optional filters:
      - `product_id`, `pattern_type`, `category`, `trend_direction`, `min_confidence`
    - Computes a **derived confidence score** based on pattern type (trend slope, volatility, seasonal amplitude, spike/dip probability).
  - `get_raw_sales(product_id, start_date, end_date) -> pd.DataFrame`
    - Reads from `sales_daily_clean` for detailed time‑series.
  - `get_forecasts(product_id) -> pd.DataFrame`
    - Reads from `forecasts`.
  - `trigger_job(params) -> str` and `get_job_status(run_id) -> dict`
    - Wrap Databricks jobs API to run and monitor a transform job.

This layer makes it easy to swap out Databricks or extend with additional tables if needed.

---

## 4. LLM & Narrative Layer (`ClaudeService`)

Located in `src/api/services/claude.py`, `ClaudeService` provides a thin abstraction over an NVIDIA NIM chat completion endpoint:

- The service is initialized with:
  - `settings.nvidia_base_url`
  - `settings.nvidia_api_key`
  - `settings.nvidia_chat_model` (fixed bug to ensure correct field is used)
- Methods:
  - `interpret_patterns(patterns_data: list[dict], user_query: str) -> str`
    - Formats a human‑readable context from the top N pattern rows.
    - Sends a system + user message to the LLM focusing on **sales patterns and recommendations**.
  - `interpret_forecast(forecast_data: dict, product_info: dict) -> str`
    - Provides a concise narrative for forecasted values with 2–3 concrete business recommendations.
  - `stream_response(patterns_data, user_query)`
    - Uses `stream=True` to progressively yield tokens for a conversational streaming endpoint (`/api/query/chat/stream`).

By centralising prompt construction here, you can easily re‑prompt or change models without touching the route handlers.

---

## 5. Caching (`CacheService`)

Located in `src/api/services/cache.py`, this service provides a simple Redis‑backed cache:

- `get(key)`, `set(key, value, ttl)`, `delete(key)`, `exists(key)`
- `pattern_key(filters: dict) -> str`
  - Normalizes and hashes filter dictionaries into stable cache keys.
- `job_key(run_id: str) -> str`
  - Namespaces job status keys.

The query and forecast routes use this cache to avoid repeated expensive Databricks calls and LLM invocations.

---

## 6. Pattern Detection & Forecasting

- **Transforms** (in `src/transforms/`):
  - Implement STFT, wavelet, and Hilbert–Huang transforms as building blocks to extract meaningful features from sales time‑series.
  - `pipeline.py` orchestrates these transforms into a consistent feature vector per time‑series.

- **Detection** (in `src/detection/`):
  - `classifier.py`:
    - Contains `PatternType` enum (`SLOW_TREND`, `HIGH_VOLATILITY`, `SUDDEN_SPIKE`, etc.).
    - Maps extracted features into a discrete pattern label.
  - `validation.py`:
    - Validates detected patterns against the original signal.
    - Computes diagnostics like overlay \(R^2\), fit quality, and human‑readable recommendations.

- **Forecasting** (in `src/forecast/pattern_based.py`):
  - `PatternForecaster` chooses a forecasting strategy depending on detected pattern type:
    - e.g., trend‑based, seasonal, volatility‑aware, etc.
  - Returns a structured object with:
    - `dates`, `values`, `lower_bound`, `upper_bound`, `confidence_interval`, `method`.

The forecast route (`/api/forecast/generate`) stitches these pieces together: it fetches pattern metadata & raw sales, runs the pattern forecaster, and asks the LLM for an explanation.

---

## 7. API Routes and Conversational Flow

### `/api/query/*`

- `POST /api/query/chat`
  - Accepts `ChatRequest { message: str, filters?: dict }`.
  - Uses a lightweight `parse_intent` function to interpret the message and infer:
    - `pattern_type` (seasonal, spike, dip, volatile, etc.)
    - `trend_direction` (increasing/decreasing)
    - optional category and minimum confidence
  - Merges inferred filters with explicit `filters` from the request.
  - Retrieves patterns via `DatabricksService.get_patterns`, applies caching, and passes results to `ClaudeService.interpret_patterns`.

- `POST /api/query/chat/stream`
  - Similar to `/chat` but returns a streaming response (`StreamingResponse`) using `ClaudeService.stream_response`.

- `GET /api/query/patterns`
  - Thin wrapper around `DatabricksService.get_patterns` with query parameters.

### `/api/forecast/*`

- `POST /api/forecast/generate`
  - Uses `ForecastRequest { product_id, horizon }`.
  - Fetches pattern metadata and raw sales for the product.
  - Infers the `PatternType` and calls `PatternForecaster`.
  - Asks `ClaudeService.interpret_forecast` to narrate the results.
  - Caches the final combined payload on `forecast:{product_id}:{horizon}`.

- `GET /api/forecast/history/{product_id}`
  - Simple Databricks query for any persisted forecasts.

### `/api/transform/*`

- `POST /api/transform/run`
  - Triggers a Databricks job using `DatabricksService.trigger_job`.
  - Intended for large‑scale pattern recomputation on the lakehouse.

- `GET /api/transform/status/{run_id}`
  - Proxies `DatabricksService.get_job_status` and stores result in cache.

- `POST /api/transform/run-local`
  - Pulls a slice of raw sales data, runs the local transform pipeline and classifier, and validates results.
  - Writes a CSV to `tests/` with a snapshot of computed features and patterns.

---

## 8. Frontend (Next.js) Overview

- Located in `frontend/` with:
  - `app/page.tsx` – main page that renders `ChatInterface`.
  - `app/components/ChatInterface.tsx` – the conversational UI.
  - `app/components/ForecastChart.tsx` – charting component for forecast responses.
  - `app/globals.css` – Tailwind‑based styling overrides.

### Chat Flow in `ChatInterface`

1. **Intent detection in the UI**
   - The `detectIntent` function classifies a user’s message as one of:
     - `query` – default mode, calls `/api/query/chat`.
     - `forecast` – calls `/api/forecast/generate` with extracted `product_id` and `horizon`.
     - `transform` – calls `/api/transform/run` to start a pipeline job.
2. **Message handling**
   - User messages are appended to local React state.
   - While awaiting responses, a loading indicator appears.
3. **Displaying results**
   - Pattern/LLM responses are shown as assistant messages.
   - Forecast responses optionally include a `forecast` payload which is passed to `ForecastChart` for visualization.

This approach keeps intent detection close to the UX while the backend focuses on data access and reasoning.

---

## 9. Extending PRISM AI

- **New pattern types**:
  - Add to `PatternType` enum and update:
    - Classifier logic
    - Confidence calculation in `DatabricksService.get_patterns`
    - Any prompts that refer to pattern names.

- **Additional BI domains**:
  - Add new routes (e.g., `/api/customer`, `/api/channel`) that reuse:
    - Databricks access pattern (`DatabricksService`)
    - LLM narrative pattern (`ClaudeService`)
    - Redis caching pattern (`CacheService`)

- **Alternative LLM providers**:
  - Extend `Settings` with new provider config.
  - Update or subclass `ClaudeService` to call a different endpoint while reusing the same public methods.

By following these patterns, you can evolve PRISM AI into a broader conversational BI assistant across multiple data domains.

