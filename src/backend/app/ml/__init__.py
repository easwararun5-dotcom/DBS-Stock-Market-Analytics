"""
Machine Learning module for DBS Stock Market Analytics.
Provides trend forecasting over 5-day horizons using supervised learning.
"""
from .features import FEATURE_COLUMNS, TARGET_THRESHOLD, CLASS_MAPPING, compute_features
from .predict import predict_ticker, get_model_status

__all__ = [
    "FEATURE_COLUMNS",
    "TARGET_THRESHOLD",
    "CLASS_MAPPING",
    "compute_features",
    "predict_ticker",
    "get_model_status",
]
