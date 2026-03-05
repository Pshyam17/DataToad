from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import pandas as pd
from src.api.dependencies import get_databricks, get_cache
from src.transforms.pipeline import TransformPipeline
from src.detection.classifier import PatternClassifier
from src.detection.validation import PatternValidator

router = APIRouter()

class TransformRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    product_ids: list[str] | None = None

@router.post("/run")
async def run_transform(request: TransformRequest, db=Depends(get_databricks), cache=Depends(get_cache)):
    params = {}
    if request.start_date:
        params["start_date"] = request.start_date
    if request.end_date:
        params["end_date"] = request.end_date
    if request.product_ids:
        params["product_ids"] = ",".join(request.product_ids)
    
    run_id = db.trigger_job(params=params)
    cache.set(cache.job_key(run_id), {"status": "PENDING", "started_at": str(datetime.utcnow())})
    return {"run_id": run_id, "status": "triggered"}

@router.get("/status/{run_id}")
async def get_transform_status(run_id: str, db=Depends(get_databricks), cache=Depends(get_cache)):
    status = db.get_job_status(run_id)
    cache.set(cache.job_key(run_id), status)
    return {"run_id": run_id, **status}

@router.post("/run-local")
async def run_transform_local(request: TransformRequest, db=Depends(get_databricks)):
    df = db.get_raw_sales(
        product_id=request.product_ids[0] if request.product_ids else None,
        start_date=request.start_date, end_date=request.end_date
    )
    if df.empty:
        return {"error": "No data found for given filters"}
    
    pipeline, classifier, validator = TransformPipeline(), PatternClassifier(), PatternValidator()
    results = []
    
    for product_id, group in df.groupby("product_id"):
        group = group.sort_values("sale_date")
        signal = group["sales_volume"].values
        dates = group["sale_date"]
        
        if len(signal) < 12:
            continue
        
        features = pipeline.extract_features(signal)
        pattern = classifier.classify(features, signal)
        validation = validator.validate(str(product_id), signal, pattern, dates)
        
        results.append({
            "product_id": product_id, **features,
            "detected_pattern": validation.detected_pattern, "confidence": validation.confidence,
            "overlay_r2": validation.overlay_r2, "fit_quality": validation.fit_quality,
            "recommendation": validation.recommendation, **validation.pattern_details
        })
    
    output_path = Path("tests") / f"transform_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    output_path.parent.mkdir(exist_ok=True)
    pd.DataFrame(results).to_csv(output_path, index=False)
    
    return {"status": "complete", "products_processed": len(results), "output_file": str(output_path), "results": results[:10]}