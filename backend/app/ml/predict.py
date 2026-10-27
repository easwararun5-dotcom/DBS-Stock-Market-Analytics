"""
Inference engine for Stock Trend Prediction.

Loads trained pipeline artifacts and evaluates live ticker data
from the TimescaleDB hypertable `public.daily_price_history`.
"""

import os
import json
from typing import Dict, Any, Optional
import joblib
import pandas as pd
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from .features import FEATURE_COLUMNS, CLASS_MAPPING, compute_features

from typing import Dict, Any, Optional, Tuple

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
PIPELINE_PATH = os.path.join(ARTIFACTS_DIR, "stock_trend_pipeline.joblib")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "metadata.json")

# In-memory singleton cache
_MODEL_CACHE: Dict[str, Any] = {
    "pipeline": None,
    "metadata": None,
}


def load_model(artifacts_dir: str = ARTIFACTS_DIR) -> Tuple[Any, Any]:
    """Loads and caches the model pipeline and metadata safely."""
    global _MODEL_CACHE
    if _MODEL_CACHE["pipeline"] is not None and _MODEL_CACHE["metadata"] is not None:
        return _MODEL_CACHE["pipeline"], _MODEL_CACHE["metadata"]

    model_path = os.path.join(artifacts_dir, "stock_trend_pipeline.joblib")
    meta_path = os.path.join(artifacts_dir, "metadata.json")

    if not os.path.exists(model_path) or not os.path.exists(meta_path):
        return None, None

    try:
        pipeline = joblib.load(model_path)
        with open(meta_path, "r") as f:
            metadata = json.load(f)
        _MODEL_CACHE["pipeline"] = pipeline
        _MODEL_CACHE["metadata"] = metadata
        return pipeline, metadata
    except Exception as e:
        print(f"[ML Predict] Error loading model artifacts: {e}")
        return None, None


def get_model_status() -> Dict[str, Any]:
    """Returns the current deployment status and metadata of the ML model."""
    pipeline, metadata = load_model()
    if pipeline is None or metadata is None:
        return {
            "ml_available": False,
            "status": "not_trained",
            "message": "Model artifacts not found. Please run the training pipeline.",
        }

    return {
        "ml_available": True,
        "status": "trained",
        "model_name": metadata.get("model_type", "unknown"),
        "model_version": metadata.get("model_version", "1.0.0"),
        "training_timestamp": metadata.get("training_timestamp"),
        "forecast_horizon": metadata.get("forecast_horizon_days", 5),
        "test_accuracy": metadata.get("test_performance", {}).get("accuracy"),
        "test_macro_f1": metadata.get("test_performance", {}).get("macro_f1"),
        "disclaimer": metadata.get("disclaimer"),
    }


def predict_ticker(ticker: str, db: Session) -> Dict[str, Any]:
    """
    Executes live trend inference for a given stock ticker.
    1. Validates ticker.
    2. Queries latest historical daily records from TimescaleDB (at least 210 trading days for MA warmup).
    3. Computes features strictly up to the latest available observation date.
    4. Generates predicted direction and class probabilities.
    """
    pipeline, metadata = load_model()
    if pipeline is None or metadata is None:
        return {
            "error": "ML model is not currently trained or available on the server.",
            "status": "model_unavailable",
        }

    # Normalize ticker (support 'TCS' and 'TCS.NS')
    raw_ticker = ticker.strip().upper()
    possible_tickers = [raw_ticker]
    if not raw_ticker.endswith(".NS"):
        possible_tickers.append(f"{raw_ticker}.NS")
    else:
        possible_tickers.append(raw_ticker[:-3])

    # Fetch latest 260 trading sessions from TimescaleDB daily_price_history
    query = text("""
        SELECT 
            trading_date AS "Date",
            ticker AS "Ticker",
            open_price AS "Open",
            high_price AS "High",
            low_price AS "Low",
            close_price AS "Close",
            volume AS "Volume"
        FROM public.daily_price_history
        WHERE ticker IN :tickers
        ORDER BY trading_date ASC
    """)
    rows = db.execute(query, {"tickers": tuple(possible_tickers)}).fetchall()

    if not rows:
        return {
            "error": f"Ticker '{ticker}' not found in active database.",
            "status": "ticker_not_found",
        }

    if len(rows) < 205:
        return {
            "error": f"Insufficient trading history ({len(rows)} days). At least 205 sessions are required for feature calculation.",
            "status": "insufficient_history",
        }

    # Build DataFrame
    df = pd.DataFrame([dict(r._mapping) for r in rows])
    actual_ticker = df["Ticker"].iloc[-1]

    # Compute features strictly using inference mode (is_training=False)
    feat_df = compute_features(df, is_training=False)

    # Extract latest observation row
    latest_row = feat_df.iloc[-1]
    latest_date = latest_row["Date_clean"].strftime("%Y-%m-%d")
    latest_close = float(latest_row["Close_clean"])

    # Extract feature vector
    X_vec = latest_row[FEATURE_COLUMNS].astype(float).values.reshape(1, -1)

    # Check for NaNs
    if np.isnan(X_vec).any():
        return {
            "error": f"Feature warmup could not be fully satisfied for {ticker}.",
            "status": "feature_warmup_error",
        }

    # Predict
    pred_class_idx = int(pipeline.predict(X_vec)[0])
    predicted_label = CLASS_MAPPING.get(pred_class_idx, "UNKNOWN")

    probabilities = {}
    confidence = 0.0
    if hasattr(pipeline, "predict_proba"):
        probs = pipeline.predict_proba(X_vec)[0]
        for idx, prob in enumerate(probs):
            cls_name = CLASS_MAPPING.get(idx, f"CLASS_{idx}")
            probabilities[cls_name] = round(float(prob), 4)
        confidence = probabilities.get(predicted_label, 0.0)

    return {
        "ticker": actual_ticker,
        "predicted_trend": predicted_label,
        "predicted_class_id": pred_class_idx,
        "confidence_score": confidence,
        "probabilities": probabilities,
        "forecast_horizon_days": metadata.get("forecast_horizon_days", 5),
        "latest_observation_date": latest_date,
        "latest_close_price": latest_close,
        "model_name": metadata.get("model_type", "RandomForest"),
        "model_version": metadata.get("model_version", "1.0.0"),
        "disclaimer": metadata.get("disclaimer"),
    }
