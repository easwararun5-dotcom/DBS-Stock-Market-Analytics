#!/usr/bin/env python3
"""
CLI entry point to train and evaluate the stock trend forecasting model.
Accepts dataset path as a configurable argument.

Usage:
    python ml/train.py [--data-path PATH] [--output-dir PATH]
"""

import sys
import os
import argparse

# Add repo root to python path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.ml.pipeline import train_and_evaluate, ARTIFACTS_DIR, REPORTS_DIR

DEFAULT_DATA_PATH = os.path.abspath(
    os.path.join(REPO_ROOT, "..", "DBS-Stock-Market-Analytics", "data", "historical", "nifty50_historical_data.csv")
)
# Fallback to local data copy if sibling is not present
if not os.path.exists(DEFAULT_DATA_PATH):
    DEFAULT_DATA_PATH = os.path.abspath(
        os.path.join(REPO_ROOT, "data", "historical", "nifty50_historical_data.csv")
    )


def main():
    parser = argparse.ArgumentParser(description="Train Stock Trend Prediction Model")
    parser.add_argument(
        "--data-path",
        type=str,
        default=DEFAULT_DATA_PATH,
        help="Path to historical stock price CSV file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=ARTIFACTS_DIR,
        help="Directory to save model artifacts",
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default=REPORTS_DIR,
        help="Directory to save evaluation reports",
    )
    args = parser.parse_args()

    if not os.path.exists(args.data_path):
        print(f"Error: Dataset not found at: {args.data_path}")
        sys.exit(1)

    print("================================================================================")
    print("DBS Stock Market Analytics — Machine Learning Pipeline")
    print(f"Dataset:    {args.data_path}")
    print(f"Output Dir: {args.output_dir}")
    print("================================================================================")

    results = train_and_evaluate(
        data_path=args.data_path,
        output_dir=args.output_dir,
        reports_dir=args.reports_dir,
    )

    print("\n================================================================================")
    print("FINAL EVALUATION SUMMARY")
    print("================================================================================")
    for model_name, data in results["models"].items():
        val_acc = data["validation"]["accuracy"]
        val_f1 = data["validation"]["macro_f1"]
        test_acc = data["test"]["accuracy"]
        test_f1 = data["test"]["macro_f1"]
        print(f"{model_name:<22} | Val Acc: {val_acc:.4f} (F1: {val_f1:.4f}) | Test Acc: {test_acc:.4f} (F1: {test_f1:.4f})")

    sel = results["selected_model"]
    print(f"\nSELECTED MODEL: {sel['name'].upper()}")
    print(f"Rationale: {sel['rationale']}")
    print("================================================================================")


if __name__ == "__main__":
    main()
