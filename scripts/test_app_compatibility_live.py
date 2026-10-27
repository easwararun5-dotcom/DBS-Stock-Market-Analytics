#!/usr/bin/env python3
"""
Exercise Application Compatibility against running backend on port 8000.
Verifies all portfolio, paper-trading, and normalized risk endpoints against dbs_disposable_validation_db.
"""
import sys
import uuid
import sys
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print(f"Connecting to backend at {BASE_URL}...")
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)
    
    # 0. Health check confirmation
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health = r.json()
    db_name = health.get("relational_database", {}).get("name")
    print(f"[HEALTH] Connected to database: {db_name}")
    assert db_name == "dbs_disposable_validation_db", f"Unexpected database: {db_name}"

    # 1. Register test user
    uid_hex = uuid.uuid4().hex[:8]
    email = f"live_compat_{uid_hex}@example.com"
    password = "TestPassword123!"
    r = client.post(f"/api/auth/register", json={
        "name": f"Compat User {uid_hex}",
        "email": email,
        "password": password
    })
    assert r.status_code == 200, f"Registration failed: {r.text}"
    auth_data = r.json()
    token = auth_data["access_token"]
    user_id = auth_data["user"]["user_id"]
    pid = auth_data["default_portfolio_id"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[AUTH] Registered user {user_id}, default portfolio {pid}")

    # 2. Check initial holdings (empty)
    r = client.get(f"/api/portfolios/{pid}/holdings", headers=headers)
    assert r.status_code == 200
    h_data = r.json()
    assert h_data["total"] == 0
    assert h_data["holdings"] == []
    print("[HOLDINGS] Initial empty holdings verified.")

    # 3. Buy 10 shares of TCS.NS @ 3000.0
    r = client.post(f"/api/portfolios/{pid}/buy", json={
        "ticker": "TCS.NS",
        "quantity": 10.0,
        "price": 3000.0
    }, headers=headers)
    assert r.status_code == 200, f"Buy failed: {r.text}"
    buy_res = r.json()
    assert buy_res["success"] is True
    assert buy_res["ticker"] == "TCS.NS"
    assert buy_res["quantity"] == 10.0
    assert buy_res["price"] == 3000.0
    print("[BUY] Bought 10 shares of TCS.NS @ 3000.0 successfully.")

    # Verify holding updated
    r = client.get(f"/api/portfolios/{pid}/holdings", headers=headers)
    assert r.status_code == 200
    h_data = r.json()
    assert h_data["total"] == 1
    tcs = h_data["holdings"][0]
    assert tcs["ticker"] == "TCS.NS"
    assert float(tcs["quantity"]) == 10.0
    assert float(tcs["invested_value"]) == 30000.0
    assert float(tcs["average_buy_price"]) == 3000.0
    print("[HOLDINGS] Post-buy holding state verified (10 shares @ 3000).")

    # 4. Partial sell 4 shares of TCS.NS @ 3200.0 (6 remain)
    r = client.post(f"/api/portfolios/{pid}/sell", json={
        "ticker": "TCS.NS",
        "quantity": 4.0,
        "price": 3200.0
    }, headers=headers)
    assert r.status_code == 200, f"Partial sell failed: {r.text}"
    sell_res = r.json()
    assert sell_res["success"] is True
    assert sell_res["remaining_shares"] == 6.0
    assert sell_res["proceeds"] == 12800.0
    print("[SELL] Partial sale of 4 shares verified (6 remain).")

    # Verify holding updated
    r = client.get(f"/api/portfolios/{pid}/holdings", headers=headers)
    assert r.status_code == 200
    tcs = r.json()["holdings"][0]
    assert float(tcs["quantity"]) == 6.0
    assert float(tcs["invested_value"]) == 18000.0
    assert float(tcs["average_buy_price"]) == 3000.0
    print("[HOLDINGS] Post-partial-sale holding state verified (6 shares @ 3000).")

    # 5. Full liquidation: sell remaining 6 shares of TCS.NS @ 3300.0
    r = client.post(f"/api/portfolios/{pid}/sell", json={
        "ticker": "TCS.NS",
        "quantity": 6.0,
        "price": 3300.0
    }, headers=headers)
    assert r.status_code == 200, f"Full liquidation failed: {r.text}"
    liq_res = r.json()
    assert liq_res["success"] is True
    assert liq_res["remaining_shares"] == 0.0
    print("[LIQUIDATION] Full liquidation of remaining 6 shares verified.")

    # Verify active holdings is now 0
    r = client.get(f"/api/portfolios/{pid}/holdings", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0
    print("[HOLDINGS] Liquidated holding excluded from active holdings.")

    # 6. Repurchase: Buy 5 shares of TCS.NS @ 3500.0 (reactivating position)
    r = client.post(f"/api/portfolios/{pid}/buy", json={
        "ticker": "TCS.NS",
        "quantity": 5.0,
        "price": 3500.0
    }, headers=headers)
    assert r.status_code == 200, f"Repurchase failed: {r.text}"
    re_res = r.json()
    assert re_res["success"] is True
    assert re_res["quantity"] == 5.0

    r = client.get(f"/api/portfolios/{pid}/holdings", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    tcs = r.json()["holdings"][0]
    assert float(tcs["quantity"]) == 5.0
    assert float(tcs["invested_value"]) == 17500.0
    assert float(tcs["average_buy_price"]) == 3500.0
    print("[REPURCHASE] Reactivated position verified (5 shares @ 3500).")

    # 7. Also buy another stock (INFY.NS) to test multi-sector risk
    r = client.post(f"/api/portfolios/{pid}/buy", json={
        "ticker": "INFY.NS",
        "quantity": 10.0,
        "price": 1500.0
    }, headers=headers)
    assert r.status_code == 200

    # Buy an Energy stock (RELIANCE.NS)
    r = client.post(f"/api/portfolios/{pid}/buy", json={
        "ticker": "RELIANCE.NS",
        "quantity": 10.0,
        "price": 2500.0
    }, headers=headers)
    assert r.status_code == 200

    # 8. Verify full transaction history intact
    r = client.get(f"/api/portfolios/{pid}/transactions", headers=headers)
    assert r.status_code == 200
    tx_data = r.json()
    assert tx_data["total"] >= 5 # 3 buys of TCS/INFY/RELIANCE + 2 sells of TCS
    print(f"[TRANSACTIONS] Transaction ledger intact with {tx_data['total']} transactions.")

    # 9. Test Risk Analysis Calculation & Read from 1NF normalized table
    r = client.post(f"/api/portfolios/{pid}/risk", headers=headers)
    assert r.status_code == 200, f"Risk calculation failed: {r.text}"
    risk_post = r.json()
    assert risk_post["success"] is True
    assert "sector_concentration" in risk_post
    print(f"[RISK POST] Computed risk analysis ID {risk_post['analysis_id']} with allocations: {risk_post['sector_concentration']}")

    # Read risk analysis back
    r = client.get(f"/api/portfolios/{pid}/risk", headers=headers)
    assert r.status_code == 200, f"Risk get failed: {r.text}"
    risk_get = r.json()
    assert risk_get["has_analysis"] is True
    allocs = risk_get["data"]["sector_concentration"]
    print(f"[RISK GET] Reconstructed 1NF allocations: {allocs}")
    assert "IT" in allocs or "Energy" in allocs
    total_pct = sum(allocs.values())
    assert 99.0 <= total_pct <= 101.0, f"Sector allocations do not sum to 100%: {total_pct}"
    print(f"[RISK GET] Total allocation sum: {total_pct}% (parity verified)")

    # 10. Test legacy compatibility endpoints
    r = client.get(f"/api/portfolio/holdings?user_id={user_id}")
    assert r.status_code == 200
    assert r.json()["total"] >= 2
    print("[LEGACY] Legacy holdings endpoint returns normalized data.")

    print("\nALL APPLICATION COMPATIBILITY CHECKS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_tests()
