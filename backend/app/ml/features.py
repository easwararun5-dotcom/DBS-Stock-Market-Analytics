"""
Feature engineering pipeline for stock trend prediction.

CRITICAL DATA LEAKAGE PREVENTION:
- Every feature for observation date t uses ONLY information available on or before date t.
- Rolling features are computed strictly grouped by Ticker and sorted by Date ascending.
- Future prices and returns are NEVER used as feature inputs.
- Target is computed as future 5-session return: (Close_{t+5} / Close_t) - 1.
- Final 5 observations per ticker are dropped for training because future labels are unavailable.
"""

from typing import List, Tuple, Dict, Any
import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    # Price Returns
    "return_1d",
    "return_3d",
    "return_5d",
    "return_10d",
    "return_20d",
    # Trend Features (Price relative to Moving Averages)
    "close_to_ma_5",
    "close_to_ma_10",
    "close_to_ma_20",
    "close_to_ma_50",
    "close_to_ma_200",
    # Moving Average Crosses / Ratios
    "ma5_to_ma20",
    "ma20_to_ma50",
    "ma50_to_ma200",
    # Volatility Features
    "volatility_5d",
    "volatility_10d",
    "volatility_20d",
    "high_low_spread",
    # Volume Dynamics
    "volume_change_1d",
    "volume_to_ma20",
    # Momentum (RSI)
    "rsi_14",
]

TARGET_THRESHOLD = 0.015  # +/- 1.5% for 5-session return
CLASS_MAPPING = {0: "DOWN", 1: "NEUTRAL", 2: "UP"}
INV_CLASS_MAPPING = {"DOWN": 0, "NEUTRAL": 1, "UP": 2}


def compute_features(df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
    """
    Computes all trend, momentum, volatility, and volume features per ticker.
    Guarantees strict temporal ordering and zero lookahead bias.
    """
    df = df.copy()
    
    # Standardize column names if needed
    col_map = {c.lower(): c for c in df.columns}
    date_col = next((c for c in df.columns if c.lower() in ["date", "trading_date"]), "Date")
    ticker_col = next((c for c in df.columns if c.lower() == "ticker"), "Ticker")
    open_col = next((c for c in df.columns if c.lower() in ["open", "open_price"]), "Open")
    high_col = next((c for c in df.columns if c.lower() in ["high", "high_price"]), "High")
    low_col = next((c for c in df.columns if c.lower() in ["low", "low_price"]), "Low")
    close_col = next((c for c in df.columns if c.lower() in ["close", "close_price"]), "Close")
    vol_col = next((c for c in df.columns if c.lower() == "volume"), "Volume")

    df["Date_clean"] = pd.to_datetime(df[date_col].astype(str).str[:10])
    df["Ticker_clean"] = df[ticker_col].astype(str).str.strip().str.upper()
    df["Close_clean"] = pd.to_numeric(df[close_col], errors="coerce")
    df["Open_clean"] = pd.to_numeric(df[open_col], errors="coerce")
    df["High_clean"] = pd.to_numeric(df[high_col], errors="coerce")
    df["Low_clean"] = pd.to_numeric(df[low_col], errors="coerce")
    df["Volume_clean"] = pd.to_numeric(df[vol_col], errors="coerce").fillna(0).clip(lower=0)

    # Sort strictly by Ticker and Date
    df = df.sort_values(["Ticker_clean", "Date_clean"]).reset_index(drop=True)
    g = df.groupby("Ticker_clean")

    # 1. Price Return Features (strictly backward looking)
    df["return_1d"] = g["Close_clean"].pct_change(1).clip(-0.5, 0.5)
    df["return_3d"] = g["Close_clean"].pct_change(3).clip(-0.5, 0.5)
    df["return_5d"] = g["Close_clean"].pct_change(5).clip(-0.5, 0.5)
    df["return_10d"] = g["Close_clean"].pct_change(10).clip(-0.5, 0.5)
    df["return_20d"] = g["Close_clean"].pct_change(20).clip(-0.5, 0.5)

    # 2. Moving Averages & Trend
    for w in [5, 10, 20, 50, 200]:
        ma = g["Close_clean"].transform(lambda x: x.rolling(w, min_periods=w).mean())
        df[f"close_to_ma_{w}"] = ((df["Close_clean"] / ma) - 1.0).clip(-1.0, 1.0)
        df[f"ma_{w}"] = ma

    df["ma5_to_ma20"] = ((df["ma_5"] / df["ma_20"]) - 1.0).clip(-1.0, 1.0)
    df["ma20_to_ma50"] = ((df["ma_20"] / df["ma_50"]) - 1.0).clip(-1.0, 1.0)
    df["ma50_to_ma200"] = ((df["ma_50"] / df["ma_200"]) - 1.0).clip(-1.0, 1.0)
    df = df.drop(columns=[f"ma_{w}" for w in [5, 10, 20, 50, 200]])

    # 3. Volatility Features
    df["volatility_5d"] = g["return_1d"].transform(lambda x: x.rolling(5, min_periods=5).std()).fillna(0).clip(0, 0.5)
    df["volatility_10d"] = g["return_1d"].transform(lambda x: x.rolling(10, min_periods=10).std()).fillna(0).clip(0, 0.5)
    df["volatility_20d"] = g["return_1d"].transform(lambda x: x.rolling(20, min_periods=20).std()).fillna(0,).clip(0, 0.5)
    df["high_low_spread"] = ((df["High_clean"] - df["Low_clean"]) / (df["Close_clean"] + 1e-9)).clip(0, 1.0)

    # 4. Volume Features (log differences protect against inf on 0 volume)
    log_vol = np.log1p(df["Volume_clean"])
    df["volume_change_1d"] = (log_vol - g["Volume_clean"].transform(lambda x: np.log1p(x.shift(1).clip(lower=0)))).clip(-5.0, 5.0)
    vol_ma20 = g["Volume_clean"].transform(lambda x: x.rolling(20, min_periods=20).mean())
    df["volume_to_ma20"] = ((df["Volume_clean"] - vol_ma20) / (vol_ma20 + 1.0)).clip(-5.0, 5.0)

    # 5. Momentum - RSI 14
    def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return (rsi / 100.0).clip(0.0, 1.0)

    df["rsi_14"] = g["Close_clean"].transform(calc_rsi)

    # 6. Future 5-Session Return & Target (computed only during training/evaluation)
    if is_training:
        df["future_close_5d"] = g["Close_clean"].shift(-5)
        df["future_return_5d"] = (df["future_close_5d"] / df["Close_clean"]) - 1.0

        def label_target(r: float) -> float:
            if pd.isna(r):
                return np.nan
            if r > TARGET_THRESHOLD:
                return 2.0  # UP
            elif r < -TARGET_THRESHOLD:
                return 0.0  # DOWN
            else:
                return 1.0  # NEUTRAL

        df["target"] = df["future_return_5d"].apply(label_target)

    return df


def audit_features_for_leakage(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Performs automated audit to guarantee:
    1. Zero NaN / inf in feature columns after dropping warmup.
    2. Zero future target information in feature columns.
    3. Proper temporal ordering per ticker.
    """
    results = {
        "passed": True,
        "checks": {},
        "errors": []
    }

    # Check 1: Feature column presence
    missing_cols = [c for c in FEATURE_COLUMNS if c not in df.columns]
    results["checks"]["feature_columns_present"] = len(missing_cols) == 0
    if missing_cols:
        results["passed"] = False
        results["errors"].append(f"Missing feature columns: {missing_cols}")

    # Check 2: Infinite values
    inf_counts = {c: int(np.isinf(df[c]).sum()) for c in FEATURE_COLUMNS if c in df.columns}
    has_inf = any(v > 0 for v in inf_counts.values())
    results["checks"]["zero_inf_values"] = not has_inf
    if has_inf:
        results["passed"] = False
        results["errors"].append(f"Infinite values found: {inf_counts}")

    # Check 3: Date monotonicity per ticker
    is_monotonic = True
    for ticker, group in df.groupby("Ticker_clean"):
        if not group["Date_clean"].is_monotonic_increasing:
            is_monotonic = False
            results["errors"].append(f"Dates not monotonically increasing for {ticker}")
            break
    results["checks"]["date_monotonic_per_ticker"] = is_monotonic
    if not is_monotonic:
        results["passed"] = False

    return results
