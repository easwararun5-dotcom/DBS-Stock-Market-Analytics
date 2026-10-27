import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestAuthAndRegistration:
    def test_register_success(self):
        email = f"alice_{uuid.uuid4().hex[:8]}@example.com"
        r = client.post("/api/auth/register", json={
            "name": "Alice Investor",
            "email": email,
            "password": "Password123!",
        })
        assert r.status_code == 200
        d = r.json()
        assert "user" in d
        assert d["user"]["email"] == email
        assert d["user"]["full_name"] == "Alice Investor"
        assert "access_token" in d
        assert "default_portfolio_id" in d

    def test_register_duplicate_email_fails(self):
        email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
        r1 = client.post("/api/auth/register", json={
            "name": "User One",
            "email": email,
            "password": "Password123!",
        })
        assert r1.status_code == 200

        r2 = client.post("/api/auth/register", json={
            "name": "User Two",
            "email": email,
            "password": "Password123!",
        })
        assert r2.status_code == 400
        assert "already exists" in r2.json()["detail"].lower()


    def test_register_invalid_email_fails(self):
        r = client.post("/api/auth/register", json={
            "name": "Bad Email",
            "email": "not-an-email",
            "password": "Password123!",
        })
        assert r.status_code == 400

    def test_register_short_password_fails(self):
        r = client.post("/api/auth/register", json={
            "name": "Short Pass",
            "email": "shortpass@example.com",
            "password": "123",
        })
        assert r.status_code == 422  # Pydantic validation error

    def test_login_success(self):
        email = f"login_success_{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/auth/register", json={
            "name": "Login User",
            "email": email,
            "password": "ValidPassword123!",
        })

        r = client.post("/api/auth/login", json={
            "email": email,
            "password": "ValidPassword123!",
        })
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["email"] == email
        assert "access_token" in d

    def test_login_wrong_password_fails(self):
        email = f"wrong_pass_{uuid.uuid4().hex[:8]}@example.com"
        client.post("/api/auth/register", json={
            "name": "Wrong Pass User",
            "email": email,
            "password": "CorrectPassword123!",
        })

        r = client.post("/api/auth/login", json={
            "email": email,
            "password": "IncorrectPassword999!",
        })
        assert r.status_code == 401
        assert "Invalid email or password" in r.json()["detail"]

    def test_get_me_unauthorized(self):
        # Using fresh client with no stored cookies
        anon_client = TestClient(app)
        r = anon_client.get("/api/auth/me")
        assert r.status_code == 401

    def test_get_me_authorized(self):
        email = f"auth_me_{uuid.uuid4().hex[:8]}@example.com"
        reg = client.post("/api/auth/register", json={
            "name": "Auth Me User",
            "email": email,
            "password": "Password123!",
        })
        token = reg.json()["access_token"]

        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["email"] == email
        assert len(d["portfolios"]) >= 1


class TestPortfolioManagementAndTrading:
    def _create_user(self, name_prefix):
        email = f"{name_prefix}_{uuid.uuid4().hex[:8]}@example.com"
        reg = client.post("/api/auth/register", json={
            "name": name_prefix.capitalize(),
            "email": email,
            "password": "Password123!",
        })
        token = reg.json()["access_token"]
        pid = reg.json()["default_portfolio_id"]
        return email, token, pid


    def test_create_and_list_portfolios(self):
        email, token, pid = self._create_user("trader_bob")
        headers = {"Authorization": f"Bearer {token}"}

        # Create second portfolio
        r_create = client.post("/api/portfolios", json={
            "portfolio_name": "Tech Growth Fund",
            "description": "High beta tech equities",
            "initial_cash": 50000.0,
        }, headers=headers)
        assert r_create.status_code == 200
        assert r_create.json()["portfolio_name"] == "Tech Growth Fund"

        # List portfolios
        r_list = client.get("/api/portfolios", headers=headers)
        assert r_list.status_code == 200
        names = [p["portfolio_name"] for p in r_list.json()["data"]]
        assert "Main Portfolio" in names
        assert "Tech Growth Fund" in names

    def test_buy_stock_success_and_holdings(self):
        email, token, pid = self._create_user("trader_carol")
        headers = {"Authorization": f"Bearer {token}"}

        # Buy 10 shares of TCS.NS at ₹3,000
        r_buy = client.post(f"/api/portfolios/{pid}/buy", json={
            "ticker": "TCS.NS",
            "quantity": 10,
            "price": 3000.0,
        }, headers=headers)
        assert r_buy.status_code == 200
        d_buy = r_buy.json()
        assert d_buy["success"] is True
        assert d_buy["quantity"] == 10
        assert d_buy["total_cost"] == 30000.0
        assert d_buy["remaining_cash"] == 70000.0  # 100,000 - 30,000

        # Verify holdings
        r_holdings = client.get(f"/api/portfolios/{pid}/holdings", headers=headers)
        assert r_holdings.status_code == 200
        d_h = r_holdings.json()
        assert d_h["cash_balance"] == 70000.0
        assert d_h["total_invested"] == 30000.0
        assert len(d_h["holdings"]) == 1
        h0 = d_h["holdings"][0]
        assert h0["ticker"] == "TCS.NS"
        assert h0["quantity"] == 10
        assert h0["average_buy_price"] == 3000.0

    def test_buy_insufficient_cash_fails(self):
        email, token, pid = self._create_user("trader_broke")
        headers = {"Authorization": f"Bearer {token}"}

        # Try to buy ₹200,000 worth of stock with only ₹100,000 cash
        r_buy = client.post(f"/api/portfolios/{pid}/buy", json={
            "ticker": "RELIANCE.NS",
            "quantity": 100,
            "price": 2000.0,  # 200,000 total cost
        }, headers=headers)
        assert r_buy.status_code == 400
        assert "Insufficient funds" in r_buy.json()["detail"]

    def test_sell_stock_and_rejection_of_overselling(self):
        email, token, pid = self._create_user("trader_seller")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Buy 20 shares of INFY.NS at ₹1,500 = ₹30,000
        client.post(f"/api/portfolios/{pid}/buy", json={
            "ticker": "INFY.NS",
            "quantity": 20,
            "price": 1500.0,
        }, headers=headers)

        # 2. Attempt to sell 25 shares (overselling -> must fail)
        r_oversell = client.post(f"/api/portfolios/{pid}/sell", json={
            "ticker": "INFY.NS",
            "quantity": 25,
            "price": 1600.0,
        }, headers=headers)
        assert r_oversell.status_code == 400
        assert "exceeds holdings" in r_oversell.json()["detail"].lower()

        # 3. Sell 10 shares (partial sale -> success)
        r_sell = client.post(f"/api/portfolios/{pid}/sell", json={
            "ticker": "INFY.NS",
            "quantity": 10,
            "price": 1600.0,
        }, headers=headers)
        assert r_sell.status_code == 200
        d_sell = r_sell.json()
        assert d_sell["remaining_shares"] == 10
        assert d_sell["proceeds"] == 16000.0
        # Initial cash 100,000 - 30,000 (buy) + 16,000 (sell) = 86,000
        assert d_sell["updated_cash"] == 86000.0

        # 4. Check transactions
        r_tx = client.get(f"/api/portfolios/{pid}/transactions", headers=headers)
        assert r_tx.status_code == 200
        tx_types = [t["transaction_type"] for t in r_tx.json()["data"]]
        assert "SELL" in tx_types
        assert "BUY" in tx_types

    def test_cross_user_portfolio_isolation(self):
        # Create User A
        _, token_a, pid_a = self._create_user("user_isolation_a")
        # Create User B
        _, token_b, pid_b = self._create_user("user_isolation_b")

        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B attempts to access User A's portfolio -> must return 404
        r_access = client.get(f"/api/portfolios/{pid_a}/holdings", headers=headers_b)
        assert r_access.status_code == 404

        # User B attempts to buy into User A's portfolio -> must return 404
        r_buy = client.post(f"/api/portfolios/{pid_a}/buy", json={
            "ticker": "TCS.NS",
            "quantity": 5,
            "price": 3000.0,
        }, headers=headers_b)
        assert r_buy.status_code == 404


class TestPersonalizedWatchlist:
    def test_watchlist_crud_and_isolation(self):
        uid_a = uuid.uuid4().hex[:8]
        uid_b = uuid.uuid4().hex[:8]
        # Register User A
        reg_a = client.post("/api/auth/register", json={
            "name": "Watchlist Alice",
            "email": f"watch_alice_{uid_a}@example.com",
            "password": "Password123!",
        })
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Register User B
        reg_b = client.post("/api/auth/register", json={
            "name": "Watchlist Bob",
            "email": f"watch_bob_{uid_b}@example.com",
            "password": "Password123!",
        })
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A adds TCS.NS
        r_add = client.post("/api/watchlist", json={"ticker": "TCS.NS", "alert_price": 3500.0}, headers=headers_a)
        assert r_add.status_code == 200

        # User A gets watchlist -> contains TCS.NS
        r_list_a = client.get("/api/watchlist", headers=headers_a)
        assert r_list_a.status_code == 200
        tickers_a = [w["ticker"] for w in r_list_a.json()["data"]]
        assert "TCS.NS" in tickers_a

        # User B gets watchlist -> empty (isolated!)
        r_list_b = client.get("/api/watchlist", headers=headers_b)
        assert r_list_b.status_code == 200
        tickers_b = [w["ticker"] for w in r_list_b.json()["data"]]
        assert "TCS.NS" not in tickers_b

        # User A deletes TCS.NS
        r_del = client.delete("/api/watchlist/TCS.NS", headers=headers_a)
        assert r_del.status_code == 200

        # User A watchlist now empty
        r_list_a2 = client.get("/api/watchlist", headers=headers_a)
        assert len(r_list_a2.json()["data"]) == 0


class TestDashboardPortfolioSync:
    def test_dashboard_portfolio_summary_consistency(self):
        uid = uuid.uuid4().hex[:8]
        reg = client.post("/api/auth/register", json={
            "name": "Sync Test User",
            "email": f"sync_{uid}@example.com",
            "password": "Password123!",
        })
        token = reg.json()["access_token"]
        pid = reg.json()["default_portfolio_id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Initial state: 100,000 cash, 0 holdings
        d_init = client.get("/api/dashboard", headers=headers).json()
        up_init = d_init["user_portfolio"]
        assert up_init is not None
        assert up_init["cash_balance"] == 100000.0
        assert up_init["total_value"] == 100000.0
        assert up_init["total_portfolio_value"] == 100000.0
        assert up_init["total_holdings"] == 0
        assert up_init["total_pl"] == 0.0

        # Buy 10 shares of RELIANCE.NS at ₹2,790.80 (cost = 27,908.00)
        buy_res = client.post(f"/api/portfolios/{pid}/buy", json={
            "ticker": "RELIANCE.NS",
            "quantity": 10,
            "price": 2790.80,
        }, headers=headers)
        assert buy_res.status_code == 200

        # Fetch Portfolio page holdings
        h_res = client.get(f"/api/portfolios/{pid}/holdings", headers=headers).json()
        assert h_res["cash_balance"] == 72092.0
        assert h_res["total_invested"] == 27908.0

        # Fetch Dashboard summary
        d_res = client.get("/api/dashboard", headers=headers).json()
        up = d_res["user_portfolio"]
        assert up is not None

        # Verify Dashboard values match Portfolio holdings values exactly
        assert up["cash_balance"] == h_res["cash_balance"]
        assert up["total_value"] == h_res["total_portfolio_value"]
        assert up["total_portfolio_value"] == h_res["total_portfolio_value"]
        assert up["invested_value"] == h_res["total_invested"]
        assert up["market_value"] == h_res["total_market_value"]
        assert up["total_pl"] == h_res["total_profit_loss"]
        assert up["unrealized_profit_loss"] == h_res["total_profit_loss"]
        assert up["total_holdings"] == len(h_res["holdings"])
        assert up["total_holdings"] == 1

    def test_dashboard_portfolio_switching(self):
        uid = uuid.uuid4().hex[:8]
        reg = client.post("/api/auth/register", json={
            "name": "Switch Test User",
            "email": f"switch_{uid}@example.com",
            "password": "Password123!",
        })
        token = reg.json()["access_token"]
        pid1 = reg.json()["default_portfolio_id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create second portfolio
        p2_res = client.post("/api/portfolios", json={
            "portfolio_name": "Second Growth Portfolio",
            "initial_cash": 60000.0,
        }, headers=headers)
        assert p2_res.status_code == 200
        pid2 = p2_res.json()["portfolio_id"]

        # Buy in portfolio 2
        client.post(f"/api/portfolios/{pid2}/buy", json={
            "ticker": "TCS.NS",
            "quantity": 5,
            "price": 3200.0,
        }, headers=headers)

        # Dashboard without param defaults to first portfolio
        d1 = client.get("/api/dashboard", headers=headers).json()
        assert d1["user_portfolio"]["portfolio_id"] == pid1
        assert d1["user_portfolio"]["cash_balance"] == 100000.0
        assert len(d1["user_portfolios"]) == 2

        # Dashboard with portfolio_id=pid2 switches to second portfolio
        d2 = client.get(f"/api/dashboard?portfolio_id={pid2}", headers=headers).json()
        assert d2["user_portfolio"]["portfolio_id"] == pid2
        assert d2["user_portfolio"]["portfolio_name"] == "Second Growth Portfolio"
        assert d2["user_portfolio"]["cash_balance"] == 44000.0  # 60,000 - 16,000
        assert d2["user_portfolio"]["total_holdings"] == 1

