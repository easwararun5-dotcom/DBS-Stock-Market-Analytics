#!/usr/bin/env python3
"""
CLI script to run live stock trend inference for a ticker symbol.

Usage:
    python ml/predict.py --ticker TCS.NS
"""

import os
import sys
import argparse

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.database import get_timescale_db
from backend.app.ml.predict import predict_ticker


def main():
    parser = argparse.ArgumentParser(description="Live Stock Trend Forecast")
    parser.add_argument("--ticker", type=str, required=True, help="Stock ticker symbol (e.g. TCS.NS or INFY)")
    args = parser.parse_args()

    session_gen = get_timescale_db()
    db = next(session_gen)
    try:
        res = predict_ticker(args.ticker, db)
        print("================================================================================")
        print("STOCK TREND FORECAST RESULT")
        print("================================================================================")
        if "error" in res:
            print(f"Status: {res['status']}")
            print(f"Error:  {res['error']}")
        else:
            print(f"Ticker:            {res['ticker']}")
            print(f"Predicted Trend:   {res['predicted_trend']} (Horizon: {res['forecast_horizon_days']} trading sessions)")
            print(f"Confidence Score:  {res['confidence_score'] * 100:.2f}%")
            print(f"Class Probs:       {res['probabilities']}")
            print(f"Latest Date:       {res['latest_observation_date']}")
            print(f"Latest Close:      ₹{res['latest_close_price']:,.2f}")
            print(f"Model:             {res['model_name']} v{res['model_version']}")
            print(f"Note:              {res['disclaimer']}")
        print("================================================================================")
    finally:
        db.close()


if __name__ == "__main__":
    main()
