#!/usr/bin/env python3
"""
CLI script to inspect and evaluate trained model artifacts against test metrics.
"""

import os
import sys
import json
import argparse

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.ml.pipeline import ARTIFACTS_DIR


def main():
    parser = argparse.ArgumentParser(description="Evaluate Trained Model Artifacts")
    parser.add_argument(
        "--artifacts-dir",
        type=str,
        default=ARTIFACTS_DIR,
        help="Path to trained artifacts directory",
    )
    args = parser.parse_args()

    meta_path = os.path.join(args.artifacts_dir, "metadata.json")
    metrics_path = os.path.join(args.artifacts_dir, "metrics.json")

    if not os.path.exists(meta_path) or not os.path.exists(metrics_path):
        print(f"Error: Artifacts not found in {args.artifacts_dir}. Run `python ml/train.py` first.")
        sys.exit(1)

    with open(meta_path, "r") as f:
        meta = json.load(f)
    with open(metrics_path, "r") as f:
        metrics = json.load(f)

    print("================================================================================")
    print("MODEL ARTIFACT EVALUATION REPORT")
    print(f"Model Name:          {meta.get('model_type')}")
    print(f"Version:             {meta.get('model_version')}")
    print(f"Trained Timestamp:   {meta.get('training_timestamp')}")
    print(f"Forecast Horizon:    {meta.get('forecast_horizon_days')} trading sessions")
    print(f"Target Threshold:    +/- {meta.get('target_threshold') * 100:.1f}%")
    print(f"Features:            {len(meta.get('feature_columns', []))} inputs")
    print("--------------------------------------------------------------------------------")
    test_perf = meta.get("test_performance", {})
    print(f"Test Accuracy:          {test_perf.get('accuracy', 0):.4f}")
    print(f"Test Balanced Accuracy: {test_perf.get('balanced_accuracy', 0):.4f}")
    print(f"Test Macro Precision:   {test_perf.get('macro_precision', 0):.4f}")
    print(f"Test Macro Recall:      {test_perf.get('macro_recall', 0):.4f}")
    print(f"Test Macro F1-Score:    {test_perf.get('macro_f1', 0):.4f}")
    print(f"Test Brier Score:       {test_perf.get('mean_brier_score', 0):.4f}")
    print("\nPer-Class Metrics on Held-Out Test Set (2024–2026):")
    for cls, vals in test_perf.get("per_class", {}).items():
        print(f"  {cls:<8} | Precision: {vals['precision']:.4f} | Recall: {vals['recall']:.4f} | F1: {vals['f1']:.4f} | Support: {vals['support']:,}")
    print("\nConfusion Matrix (Rows=True, Cols=Pred: DOWN, NEUTRAL, UP):")
    for row in test_perf.get("confusion_matrix", []):
        print(f"  {row}")
    print("================================================================================")


if __name__ == "__main__":
    main()
