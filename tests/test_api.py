"""
API tests for DBS Stock Market Analytics Backend.

Runs against live dual-database architecture:
- PostgreSQL (relational) on port 5435
- TimescaleDB (time-series Docker container) on port 5434
"""


import pytest
from fastapi.testclient import TestClient

import sys, os

# Allow import from repository root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.app.main import app

client = TestClient(app)



# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class TestHealth:
    def test_health_returns_200(self):
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_health_database_connected(self):
        r = client.get("/api/health")
        data = r.json()
        assert data["status"] == "healthy"
        assert data["database"]["connected"] is True

    def test_health_dual_databases_connected(self):
        r = client.get("/api/health")
        data = r.json()
        assert data["status"] == "healthy"
        assert data["relational_database"]["connected"] is True
        assert data["timescale_database"]["connected"] is True
        assert data["timescale_database"]["hypertable"] == "daily_price_history"



# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class TestDashboard:
    def test_dashboard_returns_200(self):
        r = client.get("/api/dashboard")
        assert r.status_code == 200

    def test_dashboard_counts(self):
        d = client.get("/api/dashboard").json()
        assert d["total_companies"] == 49
        assert d["total_sectors"] == 13
        assert d["total_price_records"] == 287310
        assert d["total_corporate_actions"] == 1653
        assert d["latest_data_date"] == "2026-01-30"

    def test_dashboard_has_gainers_losers(self):
        d = client.get("/api/dashboard").json()
        assert len(d["top_gainers"]) > 0
        assert len(d["top_losers"]) > 0
        assert len(d["sector_breakdown"]) == 13


# ---------------------------------------------------------------------------
# Latest Prices
# ---------------------------------------------------------------------------
class TestLatestPrices:
    def test_latest_prices_returns_49(self):
        r = client.get("/api/prices/latest")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 49

    def test_latest_prices_have_required_fields(self):
        rows = client.get("/api/prices/latest").json()["data"]
        for row in rows:
            assert "ticker" in row
            assert "company_name" in row
            assert "close_price" in row


# ---------------------------------------------------------------------------
# Price History
# ---------------------------------------------------------------------------
class TestPriceHistory:
    def test_price_history_for_tcs(self):
        r = client.get("/api/prices/TCS.NS?limit=10")
        assert r.status_code == 200
        data = r.json()
        assert data["ticker"] == "TCS.NS"
        assert len(data["data"]) == 10

    def test_price_history_date_range(self):
        r = client.get("/api/prices/TCS.NS?start_date=2025-01-01&end_date=2025-01-31&limit=100")
        assert r.status_code == 200
        data = r.json()
        assert len(data["data"]) > 0

    def test_price_history_fields(self):
        r = client.get("/api/prices/TCS.NS?limit=5")
        assert r.status_code == 200
        row = r.json()["data"][0]
        assert "ticker" in row
        assert "trading_date" in row
        assert "close_price" in row
        assert "open_price" in row
        assert "volume" in row
        assert "daily_return" in row
        assert "ma_50" in row
        assert "ma_200" in row

    def test_price_history_unknown_ticker(self):
        r = client.get("/api/prices/FAKEXYZ")
        assert r.status_code == 404



# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------
class TestCompanies:
    def test_list_all_companies(self):
        r = client.get("/api/companies")
        assert r.status_code == 200
        assert r.json()["total"] == 49

    def test_search_companies(self):
        r = client.get("/api/companies?search=Reliance")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any("RELIANCE" in c["ticker"] for c in data["data"])

    def test_filter_by_sector(self):
        r = client.get("/api/companies?sector=IT")
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_company_detail(self):
        r = client.get("/api/companies/TCS.NS")
        assert r.status_code == 200
        d = r.json()
        assert d["ticker"] == "TCS.NS"
        assert d["fundamentals"] is not None
        assert d["summary"] is not None
        assert d["latest_price"] is not None

    def test_company_detail_not_found(self):
        r = client.get("/api/companies/FAKEXYZ")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Sectors
# ---------------------------------------------------------------------------
class TestSectors:
    def test_sector_performance(self):
        r = client.get("/api/sectors")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 13
        for s in data["data"]:
            assert "sector_name" in s
            assert "num_companies" in s


# ---------------------------------------------------------------------------
# Stock Summary
# ---------------------------------------------------------------------------
class TestStockSummary:
    def test_stock_summary(self):
        r = client.get("/api/summary")
        assert r.status_code == 200
        assert r.json()["total"] == 49

    def test_stock_summary_sorted(self):
        r = client.get("/api/summary?sort_by=total_return_pct&order=desc")
        data = r.json()["data"]
        returns = [d["total_return_pct"] for d in data if d["total_return_pct"] is not None]
        assert returns == sorted(returns, reverse=True)


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------
class TestVolatility:
    def test_volatility_all(self):
        r = client.get("/api/volatility")
        assert r.status_code == 200
        assert r.json()["total"] == 49


# ---------------------------------------------------------------------------
# Corporate Actions
# ---------------------------------------------------------------------------
class TestCorporateActions:
    def test_corporate_actions_paginated(self):
        r = client.get("/api/corporate-actions?per_page=5")
        assert r.status_code == 200
        d = r.json()
        assert len(d["data"]) == 5
        assert d["total"] == 1653

    def test_corporate_actions_filter_ticker(self):
        r = client.get("/api/corporate-actions?ticker=TCS.NS")
        assert r.status_code == 200
        assert all(a["ticker"] == "TCS.NS" for a in r.json()["data"])

    def test_corporate_action_summary(self):
        r = client.get("/api/corporate-actions/summary")
        assert r.status_code == 200
        assert r.json()["total"] == 49


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
class TestPerformance:
    def test_stock_performance(self):
        r = client.get("/api/performance")
        assert r.status_code == 200
        assert r.json()["total"] == 49


# ---------------------------------------------------------------------------
# ML (Trained Model & Live Trend Inference)
# ---------------------------------------------------------------------------
class TestML:
    def test_ml_status_trained(self):
        r = client.get("/api/ml/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "trained"
        assert d["ml_available"] is True
        assert d["model_name"] in ["hist_gradient_boosting", "random_forest", "logistic_regression"]
        assert d["forecast_horizon"] == 5
        assert d["test_accuracy"] is not None

    def test_ml_predict_valid_ticker(self):
        r = client.get("/api/ml/predict/TCS.NS")
        assert r.status_code == 200
        d = r.json()
        assert d["ticker"] == "TCS.NS"
        assert d["predicted_trend"] in ["UP", "DOWN", "NEUTRAL"]
        assert "probabilities" in d
        assert "DOWN" in d["probabilities"]
        assert "UP" in d["probabilities"]
        assert "NEUTRAL" in d["probabilities"]
        assert d["forecast_horizon_days"] == 5
        assert d["latest_observation_date"] is not None

    def test_ml_predict_ticker_without_suffix(self):
        r = client.get("/api/ml/predict/INFY")
        assert r.status_code == 200
        d = r.json()
        assert "INFY" in d["ticker"]
        assert d["predicted_trend"] in ["UP", "DOWN", "NEUTRAL"]

    def test_ml_predict_unknown_ticker(self):
        r = client.get("/api/ml/predict/UNKNOWN_TICKER_XYZ")
        assert r.status_code == 404

    def test_ml_predictions_endpoint(self):
        r = client.get("/api/ml/predictions")
        assert r.status_code == 200
        assert "data" in r.json()


# ---------------------------------------------------------------------------
# Watchlist & Portfolio (demo mode)
# ---------------------------------------------------------------------------
class TestWatchlistPortfolio:
    def test_watchlist_returns_demo(self):
        r = client.get("/api/watchlist?user_id=1")
        assert r.status_code == 200
        assert r.json()["demo_mode"] is True

    def test_portfolio_holdings_returns_demo(self):
        r = client.get("/api/portfolio/holdings?user_id=1")
        assert r.status_code == 200
        assert r.json()["demo_mode"] is True

    def test_portfolio_transactions_returns_demo(self):
        r = client.get("/api/portfolio/transactions?user_id=1")
        assert r.status_code == 200
        assert r.json()["demo_mode"] is True


# ---------------------------------------------------------------------------
# TimescaleDB Time-Bucket Analytics
# ---------------------------------------------------------------------------
class TestTimeBucketAnalytics:
    def test_time_bucket_weekly_returns_200(self):
        r = client.get("/api/analytics/time-bucket/TCS.NS?interval=7%20days")
        assert r.status_code == 200
        d = r.json()
        assert d["ticker"] == "TCS.NS"
        assert d["interval"] == "7 days"
        assert d["total_buckets"] > 0
        first_bucket = d["data"][0]
        assert "bucket" in first_bucket
        assert "avg_close" in first_bucket
        assert "total_volume" in first_bucket
        assert "min_price" in first_bucket
        assert "max_price" in first_bucket
        assert "record_count" in first_bucket

    def test_time_bucket_date_filtered(self):
        r = client.get("/api/analytics/time-bucket/TCS.NS?interval=7%20days&start_date=2025-01-01&end_date=2025-12-31")
        assert r.status_code == 200
        d = r.json()
        assert d["total_buckets"] > 0

