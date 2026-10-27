"""
Paper Trading Verification Tests for DBS Stock Market Analytics.

Verifies all 12 requirements:
1. Register a new user.
2. Confirm a default portfolio is created with ₹100,000 virtual cash.
3. Log out and log back in.
4. Confirm the balance remains ₹100,000.
5. Buy 10 shares of RELIANCE.NS at ₹2,500.
6. Confirm the balance becomes ₹75,000.
7. Confirm the holding contains 10 shares.
8. Sell 5 shares at ₹2,600.
9. Confirm the balance becomes ₹88,000 and the holding contains 5 shares.
10. Confirm the transaction history contains both trades.
11. Verify that a different user cannot access this portfolio.
12. Verify that a purchase exceeding the available balance is rejected.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.app.main import app

client = TestClient(app)


def test_complete_paper_trading_workflow():
    unique_id = uuid.uuid4().hex[:8]
    email = f"trader_{unique_id}@example.com"
    password = "StrongPassword123!"
    name = f"Paper Trader {unique_id}"

    # 1. Register a new user
    reg_resp = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    token = reg_data["access_token"]
    user_id = reg_data["user"]["user_id"]
    default_pid = reg_data["default_portfolio_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Confirm a default portfolio is created with ₹100,000 virtual cash
    port_resp = client.get(f"/api/portfolios/{default_pid}", headers=headers)
    assert port_resp.status_code == 200
    port_data = port_resp.json()
    assert float(port_data["cash_balance"]) == 100000.0, f"Expected 100000.0, got {port_data['cash_balance']}"
    assert port_data["portfolio_name"] == "Main Portfolio"

    # Also verify through /api/portfolios list endpoint
    ports_list_resp = client.get("/api/portfolios", headers=headers)
    assert ports_list_resp.status_code == 200
    p_item = next(p for p in ports_list_resp.json()["data"] if p["portfolio_id"] == default_pid)
    assert float(p_item["cash_balance"]) == 100000.0

    # 3. Log out and log back in
    logout_resp = client.post("/api/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    login_resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    login_token = login_data["access_token"]
    login_headers = {"Authorization": f"Bearer {login_token}"}

    # 4. Confirm the balance remains ₹100,000
    relogin_port_resp = client.get(f"/api/portfolios/{default_pid}", headers=login_headers)
    assert relogin_port_resp.status_code == 200
    assert float(relogin_port_resp.json()["cash_balance"]) == 100000.0

    # 5. Buy 10 shares of RELIANCE.NS at ₹2,500
    buy_resp = client.post(
        f"/api/portfolios/{default_pid}/buy",
        headers=login_headers,
        json={"ticker": "RELIANCE.NS", "quantity": 10, "price": 2500.0},
    )
    assert buy_resp.status_code == 200, f"Buy failed: {buy_resp.text}"
    buy_data = buy_resp.json()
    assert buy_data["success"] is True
    assert buy_data["quantity"] == 10.0
    assert buy_data["price"] == 2500.0
    assert buy_data["total_cost"] == 25000.0

    # 6. Confirm the balance becomes ₹75,000
    assert buy_data["remaining_cash"] == 75000.0
    check_port = client.get(f"/api/portfolios/{default_pid}", headers=login_headers).json()
    assert float(check_port["cash_balance"]) == 75000.0

    # 7. Confirm the holding contains 10 shares
    holdings_resp = client.get(f"/api/portfolios/{default_pid}/holdings", headers=login_headers)
    assert holdings_resp.status_code == 200
    holdings_data = holdings_resp.json()
    assert float(holdings_data["cash_balance"]) == 75000.0
    holdings_list = holdings_data.get("holdings", holdings_data.get("data", []))
    rel_holding = next(h for h in holdings_list if "RELIANCE" in h["ticker"])
    assert float(rel_holding["quantity"]) == 10.0
    assert float(rel_holding["average_buy_price"]) == 2500.0
    assert float(rel_holding["invested_value"]) == 25000.0

    # 8. Sell 5 shares at ₹2,600
    sell_resp = client.post(
        f"/api/portfolios/{default_pid}/sell",
        headers=login_headers,
        json={"ticker": "RELIANCE.NS", "quantity": 5, "price": 2600.0},
    )
    assert sell_resp.status_code == 200, f"Sell failed: {sell_resp.text}"
    sell_data = sell_resp.json()
    assert sell_data["success"] is True
    assert sell_data["quantity"] == 5.0
    assert sell_data["price"] == 2600.0
    assert sell_data["proceeds"] == 13000.0

    # 9. Confirm the balance becomes ₹88,000 and the holding contains 5 shares
    assert sell_data["updated_cash"] == 88000.0
    assert sell_data["remaining_shares"] == 5.0
    check_port_after_sell = client.get(f"/api/portfolios/{default_pid}", headers=login_headers).json()
    assert float(check_port_after_sell["cash_balance"]) == 88000.0

    holdings_after_sell = client.get(f"/api/portfolios/{default_pid}/holdings", headers=login_headers).json()
    h_list = holdings_after_sell.get("holdings", holdings_after_sell.get("data", []))
    rel_after = next(h for h in h_list if "RELIANCE" in h["ticker"])
    assert float(rel_after["quantity"]) == 5.0
    assert float(rel_after["invested_value"]) == 12500.0  # 5 * 2500

    # 10. Confirm the transaction history contains both trades
    tx_resp = client.get(f"/api/portfolios/{default_pid}/transactions", headers=login_headers)
    assert tx_resp.status_code == 200
    tx_list = tx_resp.json().get("data", tx_resp.json().get("transactions", []))
    assert len(tx_list) >= 2
    types = [t["transaction_type"] for t in tx_list[:2]]
    assert "BUY" in types and "SELL" in types

    # 11. Verify that a different user cannot access this portfolio
    other_uid = uuid.uuid4().hex[:8]
    other_reg = client.post(
        "/api/auth/register",
        json={"name": "Attacker", "email": f"attacker_{other_uid}@example.com", "password": "Password123!"},
    )
    other_token = other_reg.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    denied_detail = client.get(f"/api/portfolios/{default_pid}", headers=other_headers)
    assert denied_detail.status_code in [403, 404]

    denied_buy = client.post(
        f"/api/portfolios/{default_pid}/buy",
        headers=other_headers,
        json={"ticker": "RELIANCE.NS", "quantity": 1, "price": 2500.0},
    )
    assert denied_buy.status_code in [403, 404]

    # 12. Verify that a purchase exceeding the available balance is rejected
    # Current balance is ₹88,000. Attempt to buy 100 shares at ₹2,500 = ₹250,000 > ₹88,000.
    overspend_resp = client.post(
        f"/api/portfolios/{default_pid}/buy",
        headers=login_headers,
        json={"ticker": "RELIANCE.NS", "quantity": 100, "price": 2500.0},
    )
    assert overspend_resp.status_code == 400
    assert "Insufficient funds" in overspend_resp.json()["detail"]

    # Verify balance was not deducted and remains ₹88,000
    final_port = client.get(f"/api/portfolios/{default_pid}", headers=login_headers).json()
    assert float(final_port["cash_balance"]) == 88000.0
