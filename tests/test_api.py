"""
API tests for DBS Stock Market Analytics Backend.

Runs against a live database — requires the TimescaleDB Docker container
to be running on port 5433.
"""

import pytest
from fastapi.testclient import TestClient

import sys, os

# Allow import from backend/app/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.main import app

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
# ML (deferred)
# ---------------------------------------------------------------------------
class TestML:
    def test_ml_status_not_trained(self):
        r = client.get("/api/ml/status")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "not_trained"
        assert d["ml_available"] is False

    def test_ml_predictions_empty(self):
        r = client.get("/api/ml/predictions")
        assert r.status_code == 200
        assert r.json()["total"] == 0


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
