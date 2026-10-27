"""
Unit and integration tests for the ML Pipeline, Feature Engineering,
Leakage Prevention, Model Training, Serialization, and Inference.
"""

import os
import pytest
import numpy as np
import pandas as pd
from backend.app.ml.features import (
    FEATURE_COLUMNS,
    TARGET_THRESHOLD,
    CLASS_MAPPING,
    compute_features,
    audit_features_for_leakage,
)
from backend.app.ml.pipeline import (
    split_chronological,
    train_and_evaluate,
    evaluate_predictions,
    ARTIFACTS_DIR,
)
from backend.app.ml.predict import load_model, get_model_status


@pytest.fixture
def sample_stock_df():
    """Generates synthetic multi-ticker historical price data for testing."""
    dates = pd.date_range("2020-01-01", periods=250, freq="B")
    records = []
    for ticker in ["TICKERA.NS", "TICKERB.NS"]:
        price = 100.0
        for d in dates:
            ret = np.random.normal(0.0005, 0.015)
            price *= (1 + ret)
            high = price * (1 + abs(np.random.normal(0, 0.005)))
            low = price * (1 - abs(np.random.normal(0, 0.005)))
            vol = int(np.random.uniform(10000, 50000))
            records.append({
                "Date": d.strftime("%Y-%m-%d"),
                "Ticker": ticker,
                "Open": price * (1 - ret/2),
                "High": high,
                "Low": low,
                "Close": price,
                "Volume": vol,
            })
    return pd.DataFrame(records)


class TestFeatureEngineering:
    def test_feature_columns_generated(self, sample_stock_df):
        feat_df = compute_features(sample_stock_df, is_training=True)
        for col in FEATURE_COLUMNS:
            assert col in feat_df.columns, f"Missing feature: {col}"
        assert "target" in feat_df.columns
        assert "future_return_5d" in feat_df.columns

    def test_target_labeling_logic(self):
        df = pd.DataFrame({
            "Date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06", "2023-01-07"],
            "Ticker": ["TEST.NS"] * 7,
            "Open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
            "High": [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
            "Low": [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0],
            "Close": [100.0, 100.0, 100.0, 100.0, 100.0, 105.0, 95.0],
            "Volume": [1000] * 7,
        })
        feat_df = compute_features(df, is_training=True)
        # Day 0 to Day 5: 100 to 105 -> return +5% > +1.5% -> UP (2)
        assert feat_df.loc[0, "target"] == 2.0
        # Day 1 to Day 6: 100 to 95 -> return -5% < -1.5% -> DOWN (0)
        assert feat_df.loc[1, "target"] == 0.0
        # Final 5 rows must have NaN target because t+5 does not exist
        assert pd.isna(feat_df.loc[2, "target"])
        assert pd.isna(feat_df.loc[6, "target"])

    def test_no_cross_ticker_leakage(self, sample_stock_df):
        feat_df = compute_features(sample_stock_df, is_training=True)
        # First 5 rows of TICKERB must not take lag/lead values from TICKERA
        ticker_b_start = feat_df[feat_df["Ticker_clean"] == "TICKERB.NS"].index[0]
        assert pd.isna(feat_df.loc[ticker_b_start, "return_1d"])

    def test_audit_leakage_detection(self, sample_stock_df):
        feat_df = compute_features(sample_stock_df, is_training=True)
        audit = audit_features_for_leakage(feat_df)
        assert audit["passed"] is True
        assert audit["checks"]["feature_columns_present"] is True
        assert audit["checks"]["zero_inf_values"] is True
        assert audit["checks"]["date_monotonic_per_ticker"] is True


class TestChronologicalSplits:
    def test_split_embargo_and_boundaries(self, sample_stock_df):
        # Create multi-year synthetic dataset
        dates = pd.date_range("2020-01-01", "2025-06-01", freq="B")
        rows = []
        for d in dates:
            rows.append({
                "Date": d.strftime("%Y-%m-%d"),
                "Ticker": "TCS.NS",
                "Open": 100.0, "High": 102.0, "Low": 98.0, "Close": 100.0, "Volume": 10000
            })
        df = pd.DataFrame(rows)
        feat_df = compute_features(df, is_training=True)
        train, val, test, info = split_chronological(feat_df)

        assert len(train) > 0
        assert len(val) > 0
        assert len(test) > 0

        # Max train date must be <= 2021-12-24
        assert train["Date_clean"].max() <= pd.Timestamp("2021-12-24")
        # Min val date must be >= 2022-01-01
        assert val["Date_clean"].min() >= pd.Timestamp("2022-01-01")
        # Max val date must be <= 2023-12-22
        assert val["Date_clean"].max() <= pd.Timestamp("2023-12-22")
        # Min test date must be >= 2024-01-01
        assert test["Date_clean"].min() >= pd.Timestamp("2024-01-01")


class TestModelArtifactsAndInference:
    def test_artifacts_exist_and_load(self):
        pipe, meta = load_model(ARTIFACTS_DIR)
        assert pipe is not None
        assert meta is not None
        assert meta["model_version"] in ["1.0.0", "1.1.0"]
        assert meta["forecast_horizon_days"] == 5
        assert meta["target_threshold"] == TARGET_THRESHOLD
        assert len(meta["feature_columns"]) == len(FEATURE_COLUMNS)

    def test_model_status_endpoint(self):
        status = get_model_status()
        assert status["status"] == "trained"
        assert status["ml_available"] is True
        assert status["model_name"] in ["hist_gradient_boosting", "random_forest_calibrated", "random_forest"]

    def test_class_ordering_and_mapping(self):
        pipe, meta = load_model(ARTIFACTS_DIR)
        # Verify 0 is DOWN, 1 is NEUTRAL, 2 is UP
        assert CLASS_MAPPING[0] == "DOWN"
        assert CLASS_MAPPING[1] == "NEUTRAL"
        assert CLASS_MAPPING[2] == "UP"
        assert meta["classes"]["0"] == "DOWN" or meta["classes"][0] == "DOWN"

    def test_probability_normalization_and_finiteness(self):
        pipe, meta = load_model(ARTIFACTS_DIR)
        dummy_X = np.random.normal(0, 1, size=(20, len(FEATURE_COLUMNS)))
        probs = pipe.predict_proba(dummy_X)
        assert probs.shape == (20, 3)
        assert np.isfinite(probs).all()
        assert (probs >= 0.0).all()
        # Sum must equal 1.0 within floating point precision
        row_sums = probs.sum(axis=1)
        np.testing.assert_allclose(row_sums, np.ones(20), atol=1e-5)

    def test_reproducibility_of_predictions(self):
        pipe, _ = load_model(ARTIFACTS_DIR)
        dummy_X = np.ones((5, len(FEATURE_COLUMNS))) * 0.05
        pred1 = pipe.predict(dummy_X)
        pred2 = pipe.predict(dummy_X)
        np.testing.assert_array_equal(pred1, pred2)

    def test_down_predictions_present(self):
        """Verifies the model is capable of predicting all three classes including DOWN (class 0)."""
        pipe, meta = load_model(ARTIFACTS_DIR)
        test_perf = meta.get("test_performance", {})
        down_metrics = test_perf.get("per_class", {}).get("DOWN", {})
        # Verify DOWN recall is greater than 0 on the held-out test evaluation
        assert down_metrics.get("recall", 0.0) > 0.05, f"DOWN recall remained near zero: {down_metrics.get('recall')}"
        assert down_metrics.get("support", 0) > 0
        # Verify confusion matrix shows non-zero DOWN predictions
        cm = test_perf.get("confusion_matrix", [])
        total_pred_down = sum(row[0] for row in cm)
        assert total_pred_down > 500, f"Expected non-trivial DOWN predictions, got {total_pred_down}"

    def test_evaluation_metrics_validity(self):
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 1, 0, 1, 2])
        metrics = evaluate_predictions(y_true, y_pred)
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert 0.0 <= metrics["balanced_accuracy"] <= 1.0
        assert 0.0 <= metrics["macro_f1"] <= 1.0
        assert "DOWN" in metrics["per_class"]
        assert "UP" in metrics["per_class"]
        assert "NEUTRAL" in metrics["per_class"]
