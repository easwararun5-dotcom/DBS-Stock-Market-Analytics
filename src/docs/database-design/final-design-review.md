# Final Database Design Review & Portfolio Lifecycle Resolution Report

**Project:** DBS – Stock Market Analytics and Portfolio Management System  
**Database:** `stock_market_db` (PostgreSQL 18.4, `localhost:5435`, user: `easwarap`)  
**Phase:** Pre-Backend Implementation Final Review & Lifecycle Resolution  
**Date:** 2026-10-19  
**Status:** Audit Completed; Inconsistency Resolved, Tested & Verified  

---

## 1. Executive Summary

Prior to initiating backend API development, an end-to-end architectural inspection of the database layer was conducted across:
- **13 Database Tables** and supporting schema constraints
- **6 Analytical Views**
- **5 Database Functions & 2 Stored Procedures** ([`record_stock_purchase`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/procedures/06_record_stock_purchase.sql), [`record_stock_sale`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/procedures/07_record_stock_sale.sql))
- **2 Active Triggers** (Auditing & Consistency)
- **All Integration, Lifecycle, & Regression Test Suites**

This review documents the resolution of the portfolio lifecycle inconsistency, the implementation of [`record_stock_sale`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/procedures/07_record_stock_sale.sql), the updated valuation and P&L functions, and verified test results.

---

## 2. Area 1: Portfolio Lifecycle Resolution

### 2.1 The Issue Resolved
Prior to this resolution, `portfolio_holding.quantity` was incremented by `record_stock_purchase`, but no procedure or trigger decremented it on sales. As a result, `portfolio_holding.quantity` acted as a cumulative purchase tracker, causing downstream valuation and P&L functions to report values for all shares ever bought rather than active shares held.

### 2.2 The Adopted Model
The system has standardized on a **Current Active Position Model** with proportionate weighted-average cost basis reduction:
1. **Active Remaining Position:** `portfolio_holding.quantity` strictly represents the **net active shares held**.
2. **Purchases ([`record_stock_purchase`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/procedures/06_record_stock_purchase.sql)):**
   - $Q_{new} = Q_{old} + q_{buy}$
   - $V_{new} = V_{old} + (q_{buy} \times p_{buy})$
   - $P_{avg, new} = V_{new} / Q_{new}$
3. **Partial Sales ([`record_stock_sale`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/procedures/07_record_stock_sale.sql)):**
   - $Q_{new} = Q_{old} - q_{sell}$
   - $P_{avg, new} = P_{avg, old}$ (weighted-average purchase price per share remains unchanged)
   - $V_{new} = \text{ROUND}(Q_{new} \times P_{avg, new}, 2)$ (invested cost basis reduces proportionately)
4. **Complete Sales ($q_{sell} = Q_{old}$):**
   - $Q_{new} = 0.0000$
   - $V_{new} = 0.00$
   - $P_{avg, new} = 0.0000$
   - Preserves the `portfolio_holding` record so composite FKs on `portfolio_transaction` remain intact. Subsequent purchases reactivate the holding cleanly.

---

## 3. Implementation of `record_stock_sale`

Stored procedure [`sql/procedures/07_record_stock_sale.sql`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/procedures/07_record_stock_sale.sql):
- **Input Validation:** Validates `p_quantity > 0` and `p_price >= 0` (raises `22023`). Validates user and company existence (raises `P0001`).
- **Concurrency Serialization:** Executes `SELECT ... FROM portfolio_holding WHERE user_id = ... AND ticker = ... FOR UPDATE` to exclusively lock the holding row, eliminating race conditions between concurrent sales.
- **Oversell Prevention:** Checks `IF p_quantity > v_old_quantity THEN RAISE EXCEPTION 'Insufficient shares to sell...' USING ERRCODE = '22023'`.
- **Holding Update:** Updates `quantity`, `invested_value`, and `average_buy_price` proportionately as described in Section 2.2.
- **Transaction Logging:** Inserts `SELL` row into `portfolio_transaction`, which automatically enlists in [`trg_portfolio_transaction_audit`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/triggers/01_portfolio_transaction_audit.sql) and [`trg_portfolio_transaction_consistency`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/triggers/02_portfolio_consistency.sql).

---

## 4. Updates to Portfolio Valuation and P&L Functions

1. **[`calculate_portfolio_value(p_user_id)`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/procedures/03_calculate_portfolio_value.sql):**
   - Added filter `AND ph.quantity > 0`.
   - Excludes completely closed positions ($Q = 0$).
   - Accurately reports `market_value = remaining_quantity * latest_close_price`.
2. **[`calculate_portfolio_profit_loss(p_user_id)`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/procedures/04_calculate_portfolio_profit_loss.sql):**
   - Added filter `AND ph.quantity > 0`.
   - Accurately reports `unrealised_pnl = (remaining_quantity * latest_close_price) - remaining_invested_value`.
   - Accurately reports `pnl_pct` based on remaining active cost basis.

---

## 5. Consistency Trigger Synchronization

In [`sql/triggers/02_portfolio_consistency.sql`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/triggers/02_portfolio_consistency.sql), the available shares calculation was unified:
- If explicit `BUY` transactions exist in `portfolio_transaction` for the holding, they form the ledger acquired pool: $Q_{acquired} = \sum \text{BUY}$.
- If no `BUY` transactions exist (e.g. direct holding insertion in test fixtures), $Q_{acquired} = \text{holding.quantity}$.
- $\text{Available Shares} = Q_{acquired} - \sum \text{Committed SELL Transactions}$.
- This guarantees full compatibility with `record_stock_purchase`, `record_stock_sale`, and all existing trigger regression tests.

---

## 6. Test Suite Execution & Verification

### 6.1 Portfolio Lifecycle Test Suite ([`tests/test_portfolio_lifecycle.sql`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/tests/test_portfolio_lifecycle.sql))
All 6 lifecycle scenarios executed and passed:
1. **Initial Purchase:** Bought 10 shares @ 3500; holding created (10 shares, ₹35,000 cost basis). **PASSED**
2. **Partial Sale:** Sold 4 shares @ 3600; holding reduced to 6 shares, ₹21,000 cost basis, avg ₹3,500. `SELL` transaction and audit row verified. **PASSED**
3. **Valuation & P&L After Partial Sale:** `calculate_portfolio_value` and `calculate_portfolio_profit_loss` accurately reported values on 6 remaining shares. **PASSED**
4. **Invalid Sales:** Correctly rejected 0 quantity, negative price, unowned ticker, and oversell attempt of 10 shares when 6 remained (all caught `22023`). **PASSED**
5. **Complete Sale:** Sold remaining 6 shares; holding reset to 0 shares, ₹0.00 cost basis; closed position excluded from active valuation & P&L. **PASSED**
6. **Reactivation After Complete Sale:** Repurchased 5 shares @ 3800, then 5 shares @ 4000 (weighted avg ₹3,900); sold 3 shares (7 remaining @ ₹3,900 = ₹27,300 cost basis); P&L verified. **PASSED**

### 6.2 Regression Verification
- **Trigger & Concurrency Suite ([`scripts/test_triggers.py`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/scripts/test_triggers.py)):** All 8 trigger tests + live multi-threaded concurrency race condition test + portfolio lifecycle suite **PASSED**.
- **Analytical SQL Suite ([`scripts/test_queries.py`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/scripts/test_queries.py)):** **10/10 files passed (50 queries, 0 failures)**.
- **Database Cleanliness:** Residual counts for `app_user`, `portfolio_holding`, `portfolio_transaction`, and `portfolio_transaction_audit` confirmed at **0 rows**.
- **Market Data Invariance:** Row counts match baselines exactly across all 6 market data tables.

---

## 7. Limitations & Future Notes

1. **Corporate Action Adjustments:** Corporate action events (stock splits and dividends) currently exist in market data only; user portfolio propagation remains an explicit transaction event or batch procedure for future implementation.
2. **Holding Ticker Uniqueness:** While `record_stock_purchase` and `record_stock_sale` enforce single consolidated holdings per ticker in application code, a schema-level `CONSTRAINT uq_holding_user_ticker UNIQUE (user_id, ticker)` remains recommended for future migration windows.
