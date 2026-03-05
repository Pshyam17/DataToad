from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.api.routes import query, transform, forecast
from src.api.dependencies import get_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    get_cache().client.close()

app = FastAPI(title="PRISM AI", description="Sales Pattern Detection & Forecasting API", version="0.1.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(query.router, prefix="/api/query", tags=["Query"])
app.include_router(transform.router, prefix="/api/transform", tags=["Transform"])
app.include_router(forecast.router, prefix="/api/forecast", tags=["Forecast"])

@app.get("/")
async def root():
    return {"message": "Prism AI API is running", "docs_url": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port)
