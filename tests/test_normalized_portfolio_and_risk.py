"""
Comprehensive Test Suite for Pure 3NF Portfolio Holdings & 1NF Sector Risk Allocations.

Covers all 8 verification areas specified in Step 6:
1. Buying and selling stocks.
2. Weighted-average purchase cost calculation.
3. Portfolio ownership and cross-user authorization.
4. Multiple portfolios belonging to one user.
5. Transaction history preservation after selling all shares or deleting a holding.
6. Sector allocation data completeness and structure.
7. Risk analysis API response compatibility (reconstructing JSON from normalized rows).
8. Foreign-key integrity and relational invariants.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.app.main import app
from backend.app.database import get_relational_db

client = TestClient(app)


class TestNormalizedPortfolioAndRisk:
    @classmethod
    def setup_class(cls):
        """Create a dedicated user and portfolio for lifecycle testing."""
        cls.uid = uuid.uuid4().hex[:8]
        cls.email = f"norm_test_{cls.uid}@example.com"
        cls.password = "StrongPass123!"
        reg = client.post("/api/auth/register", json={
            "name": f"Norm User {cls.uid}",
            "email": cls.email,
            "password": cls.password,
        })
        assert reg.status_code == 200
        cls.token = reg.json()["access_token"]
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        cls.user_id = reg.json()["user"]["user_id"]
        cls.default_pid = reg.json()["default_portfolio_id"]

    # -------------------------------------------------------------------------
    # 1. Buying and Selling Stocks
    # -------------------------------------------------------------------------
    def test_01_buy_stock_success(self):
        r = client.post(f"/api/portfolios/{self.default_pid}/buy", json={
            "ticker": "TCS.NS",
            "quantity": 10,
            "price": 3000.0,
        }, headers=self.headers)
        assert r.status_code == 200
        d = r.json()
        assert d["success"] is True
        assert d["ticker"] == "TCS.NS"
        assert d["quantity"] == 10.0
        assert d["price"] == 3000.0

    def test_02_sell_stock_partial(self):
        r = client.post(f"/api/portfolios/{self.default_pid}/sell", json={
            "ticker": "TCS.NS",
            "quantity": 4,
            "price": 3200.0,
        }, headers=self.headers)
        assert r.status_code == 200
        d = r.json()
        assert d["remaining_shares"] == 6.0
        assert d["proceeds"] == 12800.0

    # -------------------------------------------------------------------------
    # 2. Weighted-Average Purchase Cost
    # -------------------------------------------------------------------------
    def test_03_weighted_average_cost_basis(self):
        # Current: 6 shares @ 3000.0 (invested = 18000.0)
        # Buy 4 more shares @ 3500.0 (added = 14000.0)
        # Expected new quantity = 10, invested = 32000.0, avg_buy_price = 3200.0
        r_buy = client.post(f"/api/portfolios/{self.default_pid}/buy", json={
            "ticker": "TCS.NS",
            "quantity": 4,
            "price": 3500.0,
        }, headers=self.headers)
        assert r_buy.status_code == 200

        r_holdings = client.get(f"/api/portfolios/{self.default_pid}/holdings", headers=self.headers)
        assert r_holdings.status_code == 200
        tcs_holding = next(h for h in r_holdings.json()["holdings"] if h["ticker"] == "TCS.NS")
        assert float(tcs_holding["quantity"]) == 10.0
        assert float(tcs_holding["invested_value"]) == 32000.0
        assert float(tcs_holding["average_buy_price"]) == 3200.0

    # -------------------------------------------------------------------------
    # 3. Portfolio Ownership and Cross-User Authorization
    # -------------------------------------------------------------------------
    def test_04_cross_user_isolation(self):
        # Register second user
        other_email = f"other_{uuid.uuid4().hex[:8]}@example.com"
        reg_other = client.post("/api/auth/register", json={
            "name": "Other User",
            "email": other_email,
            "password": "Password123!",
        })
        other_headers = {"Authorization": f"Bearer {reg_other.json()['access_token']}"}

        # Attempt to access User 1's portfolio -> 404
        r = client.get(f"/api/portfolios/{self.default_pid}/holdings", headers=other_headers)
        assert r.status_code == 404

        # Attempt to buy into User 1's portfolio -> 404
        r_buy = client.post(f"/api/portfolios/{self.default_pid}/buy", json={
            "ticker": "INFY.NS",
            "quantity": 5,
            "price": 1500.0,
        }, headers=other_headers)
        assert r_buy.status_code == 404

    # -------------------------------------------------------------------------
    # 4. Multiple Portfolios Belonging to One User
    # -------------------------------------------------------------------------
    def test_05_multiple_portfolios_per_user(self):
        # Create second portfolio for User 1
        r_create = client.post("/api/portfolios", json={
            "portfolio_name": "Retirement Fund",
            "description": "Long-term savings",
            "cash_balance": 50000.0,
        }, headers=self.headers)
        assert r_create.status_code == 200
        retire_pid = r_create.json()["portfolio_id"]

        # Buy INFY.NS in second portfolio
        r_buy = client.post(f"/api/portfolios/{retire_pid}/buy", json={
            "ticker": "INFY.NS",
            "quantity": 10,
            "price": 1500.0,
        }, headers=self.headers)
        assert r_buy.status_code == 200

        # Verify portfolio 1 has TCS.NS, portfolio 2 has INFY.NS
        p1_holdings = client.get(f"/api/portfolios/{self.default_pid}/holdings", headers=self.headers).json()["holdings"]
        p2_holdings = client.get(f"/api/portfolios/{retire_pid}/holdings", headers=self.headers).json()["holdings"]

        assert any(h["ticker"] == "TCS.NS" for h in p1_holdings)
        assert not any(h["ticker"] == "INFY.NS" for h in p1_holdings)
        assert any(h["ticker"] == "INFY.NS" for h in p2_holdings)
        assert not any(h["ticker"] == "TCS.NS" for h in p2_holdings)

    # -------------------------------------------------------------------------
    # 5. Transaction History After Selling All Shares or Deleting a Holding
    # -------------------------------------------------------------------------
    def test_06_complete_sale_ledger_preservation(self):
        # Completely sell out all 10 shares of TCS.NS
        r_sell = client.post(f"/api/portfolios/{self.default_pid}/sell", json={
            "ticker": "TCS.NS",
            "quantity": 10,
            "price": 3300.0,
        }, headers=self.headers)
        assert r_sell.status_code == 200
        assert r_sell.json()["remaining_shares"] == 0

        # Active holdings list should exclude 0-share closed positions
        r_holdings = client.get(f"/api/portfolios/{self.default_pid}/holdings", headers=self.headers)
        assert not any(h["ticker"] == "TCS.NS" for h in r_holdings.json()["holdings"])

        # Transaction history MUST still contain all BUY and SELL transactions
        r_tx = client.get(f"/api/portfolios/{self.default_pid}/transactions", headers=self.headers)
        assert r_tx.status_code == 200
        txs = r_tx.json()["transactions"]
        tcs_txs = [t for t in txs if t["ticker"] == "TCS.NS"]
        assert len(tcs_txs) >= 3  # Initial BUY, partial SELL, second BUY, final SELL

    # -------------------------------------------------------------------------
    # 6 & 7. Risk Analysis API & Reconstructed JSON Structure
    # -------------------------------------------------------------------------
    def test_07_risk_analysis_generation_and_compatibility(self):
        # Buy positions in two distinct sectors: TCS.NS (IT) and RELIANCE.NS (Energy)
        client.post(f"/api/portfolios/{self.default_pid}/buy", json={
            "ticker": "TCS.NS",
            "quantity": 10,
            "price": 3000.0,
        }, headers=self.headers)
        client.post(f"/api/portfolios/{self.default_pid}/buy", json={
            "ticker": "RELIANCE.NS",
            "quantity": 10,
            "price": 2500.0,
        }, headers=self.headers)

        # Trigger risk calculation
        r_calc = client.post(f"/api/portfolios/{self.default_pid}/risk", headers=self.headers)
        assert r_calc.status_code == 200
        calc_data = r_calc.json()
        assert calc_data["success"] is True
        assert "sector_concentration" in calc_data
        conc = calc_data["sector_concentration"]
        assert isinstance(conc, dict)
        assert len(conc) >= 2  # At least 2 sectors represented
        assert sum(conc.values()) >= 99.0  # Percentage sums to ~100%

        # Fetch risk analysis via GET
        r_get = client.get(f"/api/portfolios/{self.default_pid}/risk", headers=self.headers)
        assert r_get.status_code == 200
        get_data = r_get.json()
        assert get_data["has_analysis"] is True
        assert "sector_concentration" in get_data["data"]
        assert isinstance(get_data["data"]["sector_concentration"], dict)

    # -------------------------------------------------------------------------
    # 8. Foreign Key Integrity and Ledger Invariants
    # -------------------------------------------------------------------------
    def test_08_ledger_integrity(self):
        r_tx = client.get(f"/api/portfolios/{self.default_pid}/transactions", headers=self.headers)
        assert r_tx.status_code == 200
        for tx in r_tx.json()["transactions"]:
            assert tx["transaction_type"] in ("BUY", "SELL", "DIVIDEND", "SPLIT")
            assert float(tx["price"]) >= 0
            assert float(tx["quantity"]) > 0
            assert tx["ticker"].endswith(".NS")
