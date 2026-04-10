"""ML API routes — classification, yield forecasting, feature importance, drift detection."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.models.database import User
from app.services.auth_service import get_current_user
import app.services.ml_service as ml

logger = structlog.get_logger()

router = APIRouter()


class PredictFailureRequest(BaseModel):
    records: list[dict[str, float]]


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

@router.post("/train/{product_id}")
async def train_models(product_id: str, _: User = Depends(get_current_user)) -> dict[str, Any]:
    """Train (or retrain) the classifier and yield predictor for a product."""
    try:
        clf = ml.train_classifier(product_id)
        reg = ml.train_yield_predictor(product_id)
        return {"classifier": clf, "yield_predictor": reg}
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("ml_service_error", endpoint=str(e.__class__.__name__), detail=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

@router.post("/predict-failure/{product_id}")
async def predict_failure(
    product_id: str,
    body: PredictFailureRequest,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Predict pass/fail for one or more measurement records."""
    if not body.records:
        raise HTTPException(status_code=422, detail="records must not be empty")
    try:
        return ml.predict_failure(product_id, body.records)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("ml_service_error", endpoint=str(e.__class__.__name__), detail=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/feature-importance/{product_id}")
async def feature_importance(
    product_id: str,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return normalized feature importances from the trained classifier."""
    try:
        return ml.get_feature_importance(product_id)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("ml_service_error", endpoint=str(e.__class__.__name__), detail=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# Yield forecasting
# ---------------------------------------------------------------------------

@router.get("/yield-forecast/{product_id}")
async def yield_forecast(
    product_id: str,
    last_n_batches: int = Query(10, ge=1, le=100),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Predict yield rate for the most recent N batches and compare to actuals."""
    try:
        return ml.forecast_yield(product_id, last_n_batches=last_n_batches)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("ml_service_error", endpoint=str(e.__class__.__name__), detail=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------

@router.get("/drift-status/{product_id}")
async def drift_status(
    product_id: str,
    ref_n: int = Query(1000, ge=100),
    recent_n: int = Query(500, ge=50),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """KS-test drift detection comparing oldest ref_n records vs most recent recent_n."""
    try:
        return ml.check_drift(product_id, ref_n=ref_n, recent_n=recent_n)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("ml_service_error", endpoint=str(e.__class__.__name__), detail=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
