"""
ML service: pass/fail classification, yield prediction, and drift detection.

Model selection (from benchmark results):
  - Classifier:      LightGBM (fastest, best AUC on tabular data; falls back to HistGradientBoosting)
  - Yield predictor: XGBoostRegressor (best RMSE on batch-level aggregates; falls back to Ridge)
  - Drift detection: KS-test per feature (no extra deps required)

Models are persisted as pickle files under /data/models/ and lazy-loaded on first use.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import structlog

from app.config.loader import get_product
from app.settings import settings

logger = structlog.get_logger()

_MODELS_DIR = Path(settings.parquet_dir).parent / "models"


def _ensure_models_dir() -> None:
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)


def _metric_cols(product_id: str) -> list[str]:
    product = get_product(product_id)
    if product is None:
        raise ValueError(f"Unknown product: {product_id}")
    return [m["name"] for m in product["metrics"]]


def _load_parquet(product_id: str) -> pl.DataFrame:
    path = Path(settings.parquet_dir) / f"{product_id}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No data for product '{product_id}'. Generate synthetic data first.")
    return pl.read_parquet(str(path))


def _build_feature_matrix(product_id: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (X, y, feature_names) for classification."""
    df = _load_parquet(product_id)
    features = _metric_cols(product_id)
    X = df.select(features).to_numpy().astype(np.float32)
    y = (df["status"] == "failed").to_numpy().astype(int)
    return X, y, features


def _build_batch_features(product_id: str) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """Return (Xb, yb, feat_cols, batch_ids) for yield prediction."""
    df = _load_parquet(product_id)
    features = _metric_cols(product_id)
    agg_exprs = (
        [pl.col(f).mean().alias(f"{f}_mean") for f in features]
        + [pl.col(f).std().alias(f"{f}_std") for f in features]
        + [(1 - (pl.col("status") == "failed").mean()).alias("yield_rate")]
    )
    batch_df = df.group_by("batch_id").agg(agg_exprs)
    feat_cols = [c for c in batch_df.columns if c not in ("batch_id", "yield_rate")]
    Xb = np.nan_to_num(batch_df.select(feat_cols).to_numpy().astype(np.float32))
    yb = batch_df["yield_rate"].to_numpy().astype(np.float32)
    batch_ids = batch_df["batch_id"].to_list()
    return Xb, yb, feat_cols, batch_ids


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def _clf_path(product_id: str) -> Path:
    return _MODELS_DIR / f"{product_id}_clf.pkl"


def train_classifier(product_id: str) -> dict[str, Any]:
    _ensure_models_dir()
    X, y, features = _build_feature_matrix(product_id)
    split = int(len(X) * 0.8)
    X_train, y_train = X[:split], y[:split]

    try:
        import lightgbm as lgb
        scale_pos = float((y_train == 0).sum()) / max(float((y_train == 1).sum()), 1)
        clf = lgb.LGBMClassifier(
            n_estimators=100, scale_pos_weight=scale_pos,
            random_state=42, verbose=-1, n_jobs=-1,
        )
        model_name = "LightGBM"
    except ImportError:
        from sklearn.ensemble import HistGradientBoostingClassifier
        clf = HistGradientBoostingClassifier(
            max_iter=100, class_weight="balanced", random_state=42
        )
        model_name = "HistGradientBoosting"

    clf.fit(X_train, y_train)
    bundle = {"model": clf, "features": features, "model_name": model_name}
    with open(_clf_path(product_id), "wb") as f:
        pickle.dump(bundle, f)
    _clf_cache[product_id] = bundle
    logger.info("Classifier trained", product=product_id, model=model_name, n=len(X_train))
    return {"status": "trained", "model": model_name, "product_id": product_id, "n_samples": len(X_train)}


_clf_cache: dict[str, Any] = {}


def _get_clf(product_id: str) -> dict[str, Any]:
    if product_id not in _clf_cache:
        path = _clf_path(product_id)
        if path.exists():
            with open(path, "rb") as f:
                _clf_cache[product_id] = pickle.load(f)
        else:
            train_classifier(product_id)
    return _clf_cache[product_id]


def predict_failure(product_id: str, records: list[dict[str, float]]) -> dict[str, Any]:
    bundle = _get_clf(product_id)
    clf, features = bundle["model"], bundle["features"]
    X = np.array([[r.get(f, 0.0) for f in features] for r in records], dtype=np.float32)
    preds = clf.predict(X)
    probs = clf.predict_proba(X)[:, 1]
    return {
        "product_id": product_id,
        "model": bundle["model_name"],
        "features": features,
        "predictions": [
            {"failed": bool(p), "failure_probability": round(float(s), 4)}
            for p, s in zip(preds, probs)
        ],
    }


def get_feature_importance(product_id: str) -> dict[str, Any]:
    bundle = _get_clf(product_id)
    clf, features = bundle["model"], bundle["features"]
    try:
        raw = clf.feature_importances_
        total = raw.sum() or 1.0
        importances = {f: round(float(v / total), 4) for f, v in zip(features, raw)}
    except AttributeError:
        importances = {f: None for f in features}
    return {
        "product_id": product_id,
        "model": bundle["model_name"],
        "importances": dict(sorted(importances.items(), key=lambda x: -(x[1] or 0))),
    }


# ---------------------------------------------------------------------------
# Yield predictor
# ---------------------------------------------------------------------------

def _reg_path(product_id: str) -> Path:
    return _MODELS_DIR / f"{product_id}_reg.pkl"


def train_yield_predictor(product_id: str) -> dict[str, Any]:
    _ensure_models_dir()
    Xb, yb, feat_cols, _ = _build_batch_features(product_id)
    split = int(len(Xb) * 0.8)
    Xb_train, yb_train = Xb[:split], yb[:split]

    try:
        import xgboost as xgb
        reg = xgb.XGBRegressor(n_estimators=100, random_state=42, device="cpu", verbosity=0)
        model_name = "XGBoostRegressor"
    except ImportError:
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        reg = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
        model_name = "Ridge"

    reg.fit(Xb_train, yb_train)
    bundle = {"model": reg, "features": feat_cols, "model_name": model_name}
    with open(_reg_path(product_id), "wb") as f:
        pickle.dump(bundle, f)
    _reg_cache[product_id] = bundle
    logger.info("Yield predictor trained", product=product_id, model=model_name, n_batches=len(Xb_train))
    return {"status": "trained", "model": model_name, "product_id": product_id, "n_batches": len(Xb_train)}


_reg_cache: dict[str, Any] = {}


def _get_reg(product_id: str) -> dict[str, Any]:
    if product_id not in _reg_cache:
        path = _reg_path(product_id)
        if path.exists():
            with open(path, "rb") as f:
                _reg_cache[product_id] = pickle.load(f)
        else:
            train_yield_predictor(product_id)
    return _reg_cache[product_id]


def forecast_yield(product_id: str, last_n_batches: int = 10) -> dict[str, Any]:
    df = _load_parquet(product_id)
    features = _metric_cols(product_id)
    bundle = _get_reg(product_id)
    reg, feat_cols = bundle["model"], bundle["features"]

    agg_exprs = (
        [pl.col(f).mean().alias(f"{f}_mean") for f in features]
        + [pl.col(f).std().alias(f"{f}_std") for f in features]
        + [(1 - (pl.col("status") == "failed").mean()).alias("actual_yield")]
    )
    batch_df = df.group_by("batch_id").agg(agg_exprs).sort("batch_id").tail(last_n_batches)
    Xb = np.nan_to_num(batch_df.select(feat_cols).to_numpy().astype(np.float32))
    preds = reg.predict(Xb)
    actual = batch_df["actual_yield"].to_numpy()

    return {
        "product_id": product_id,
        "model": bundle["model_name"],
        "batches": batch_df["batch_id"].to_list(),
        "predicted_yield": [round(float(p), 4) for p in preds],
        "actual_yield": [round(float(a), 4) for a in actual],
    }


# ---------------------------------------------------------------------------
# Drift detection (KS-test, no extra deps)
# ---------------------------------------------------------------------------

def check_drift(product_id: str, ref_n: int = 1000, recent_n: int = 500) -> dict[str, Any]:
    """Compare oldest ref_n records vs most recent recent_n records per metric."""
    from scipy.stats import ks_2samp

    df = _load_parquet(product_id)
    features = _metric_cols(product_id)

    if len(df) < ref_n + recent_n:
        return {"product_id": product_id, "status": "insufficient_data", "required": ref_n + recent_n, "available": len(df)}

    ref = df.head(ref_n).select(features).to_numpy()
    recent = df.tail(recent_n).select(features).to_numpy()

    feature_results: dict[str, Any] = {}
    for i, f in enumerate(features):
        stat, pval = ks_2samp(ref[:, i], recent[:, i])
        feature_results[f] = {
            "ks_stat": round(float(stat), 4),
            "p_value": round(float(pval), 6),
            "drift": bool(pval < 0.01),
        }

    any_drift = any(v["drift"] for v in feature_results.values())
    drifting = [f for f, v in feature_results.items() if v["drift"]]
    logger.info("Drift check complete", product=product_id, drift_detected=any_drift, drifting_features=drifting)
    return {
        "product_id": product_id,
        "drift_detected": any_drift,
        "drifting_features": drifting,
        "features": feature_results,
    }
