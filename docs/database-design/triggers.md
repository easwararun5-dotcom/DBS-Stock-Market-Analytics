# Database Triggers Specification, Audit Review & Verification Report

**Project:** DBS – Stock Market Analytics and Portfolio Management System  
**Database:** `stock_market_db` (PostgreSQL 18.4, `localhost:5435`, user: `easwarap`)  
**Phase:** Database Triggers & Consistency Review  
**Date:** 2026-10-19  
**Status:** Correctness Reviewed, Strengthened, Catalog Verified, and All Tests Passed  

---

## 1. Overview and Trigger Architecture

This document specifies the database triggers implemented and verified for the DBS Stock Market Analytics system. The trigger layer provides automated, transaction-level auditing, cross-table referential alignment, accurate sell validation, and concurrency serialization for the portfolio management domain.

### Evaluation of Trigger Requirements

| Area | Consideration | Decision | Justification |
| :--- | :--- | :--- | :--- |
| **A. Portfolio Transaction Auditing** | Audit INSERT, UPDATE, DELETE on `portfolio_transaction` | **IMPLEMENTED** | Financial transactions require an automated audit ledger capturing every mutation, prior values, timestamps, and database users. |
| **B. Timestamp Maintenance** | Automatic maintenance of `updated_at` columns | **NOT APPLICABLE** | Catalog inspection confirmed that **zero tables** in `stock_market_db` possess an `updated_at` column. Per project instructions (*"Only implement for tables with an appropriate updated_at column. Do not assume such columns exist. Avoid unnecessary schema modifications"*), no tables were altered. |
| **C. Portfolio Consistency** | Consistency vs. `record_stock_purchase` procedure | **IMPLEMENTED (Corrected & Hardened)** | `record_stock_purchase` manages holding cost-basis calculations. The consistency trigger enforces cross-table ticker alignment, accurate sell limits (accounting for previous sales and updates), row-level concurrency locking, and transaction immutability. |

---

## 2. SELL Validation Model & Source of Truth (Task 1 Resolution)

### 2.1 The Issue with Naïve Holding Checks
A naïve consistency check that merely compares a new `SELL` quantity against `portfolio_holding.quantity` permits catastrophic overselling. If a user holds 10 shares and executes a `SELL` of 7 shares, `portfolio_holding.quantity` (which tracks total purchased shares accumulated via `record_stock_purchase`) remains 10. A subsequent `SELL` of 5 shares would evaluate `5 <= 10` and be erroneously accepted, resulting in 12 shares sold from a 10-share holding.

### 2.2 The Correct Source of Truth
The correct remaining shares for any holding or ticker position are determined by:

$$\text{Available Shares} = \text{Holding Acquired Quantity} - \sum \text{Previous Committed SELL Quantities}$$

1. **Holding as the Acquired Baseline:** In this schema, `portfolio_holding.quantity` is maintained by `record_stock_purchase` as the cumulative purchased position. Using `portfolio_holding.quantity` directly as the baseline accounts for all purchases without double-counting `BUY` transaction records.
2. **Subtracting Historical Sales:** All existing transactions in `portfolio_transaction` with `transaction_type = 'SELL'` referencing the holding are aggregated.
3. **Handling Updates on Existing Sales:** During an `UPDATE` on a `SELL` transaction, the transaction's own `transaction_id` is excluded from the historical sales sum (`transaction_id <> NEW.transaction_id`). This ensures the transaction's prior allocation is freed before validating the newly requested quantity.
4. **Concurrency Serialization:** To prevent race conditions where two concurrent sessions attempt to sell remaining shares simultaneously, the trigger executes `SELECT ... FROM portfolio_holding WHERE holding_id = ... FOR UPDATE`. This row-level lock serializes competing transactions, guaranteeing that each session reads the committed transaction history before validating remaining shares.

---

## 3. Trigger Definitions and Database Objects

### 3.1 Portfolio Transaction Audit Trigger

- **Trigger Name:** `trg_portfolio_transaction_audit`
- **Target Table:** `portfolio_transaction`
- **Event Timing:** `AFTER INSERT OR UPDATE OR DELETE` (FOR EACH ROW)
- **Function:** `fn_audit_portfolio_transaction()`
- **SQL Script:** [`sql/triggers/01_portfolio_transaction_audit.sql`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/triggers/01_portfolio_transaction_audit.sql)

#### Supporting Audit Table: `portfolio_transaction_audit`

```sql
CREATE TABLE IF NOT EXISTS portfolio_transaction_audit (
    audit_id SERIAL PRIMARY KEY,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    transaction_id INTEGER NOT NULL,
    holding_id INTEGER,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    price NUMERIC(14,4) NOT NULL,
    quantity NUMERIC(20,4) NOT NULL,
    old_price NUMERIC(14,4),
    old_quantity NUMERIC(20,4),
    audit_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    audit_user TEXT NOT NULL DEFAULT CURRENT_USER
);
```

#### Supporting Indexes
- `idx_audit_transaction_id ON portfolio_transaction_audit(transaction_id)`
- `idx_audit_user_id ON portfolio_transaction_audit(user_id)`
- `idx_audit_timestamp ON portfolio_transaction_audit(audit_timestamp)`

---

### 3.2 Portfolio Consistency and Integrity Trigger

- **Trigger Name:** `trg_portfolio_transaction_consistency`
- **Target Table:** `portfolio_transaction`
- **Event Timing:** `BEFORE INSERT OR UPDATE` (FOR EACH ROW)
- **Function:** `fn_enforce_portfolio_transaction_consistency()`
- **SQL Script:** [`sql/triggers/02_portfolio_consistency.sql`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/sql/triggers/02_portfolio_consistency.sql)

#### Behavior and Integrity Rules
1. **Cross-table Ticker & Holding Alignment:** Verifies that `portfolio_holding.ticker = NEW.ticker` and `portfolio_holding.user_id = NEW.user_id`. Automatically resolves and links `holding_id` if omitted.
2. **Accurate Sell Limit Enforcement:** Calculates `available_shares = holding_quantity - already_sold`. When `TG_OP = 'UPDATE'`, excludes `NEW.transaction_id` from `already_sold`. Raises `22023 (invalid_parameter_value)` if `NEW.quantity > available_shares`.
3. **Row-level Concurrency Locking:** Acquires `FOR UPDATE` lock on `portfolio_holding` to serialize concurrent sales.
4. **Ledger Immutability on UPDATE:** Disallows modification of `transaction_id`, `user_id`, `ticker`, and `transaction_type`. Raises `23514 (check_violation)`.

---

## 4. Audit Design Review: Guarantees vs. Non-Guarantees (Task 3)

A rigorous database design must not overstate its security properties. The guarantees and non-guarantees of the audit implementation are documented below:

### What the Audit Trigger GUARANTEES
1. **Automatic DML Capture:** Any standard SQL `INSERT`, `UPDATE`, or `DELETE` executed against `portfolio_transaction` automatically invokes `fn_audit_portfolio_transaction()`.
2. **Historical State Preservation:**
   - On `INSERT`: Captures initial transaction state (`old_price` and `old_quantity` are `NULL`).
   - On `UPDATE`: Captures the new values while preserving previous financial values (`old_price`, `old_quantity`).
   - On `DELETE`: Captures the final state of the transaction prior to removal.
3. **Atomic Transaction Enlistment:** The audit record is created within the exact same database transaction as the underlying change. If the transaction rolls back, the audit record rolls back; if it commits, the audit row commits.
4. **Session Metadata Capture:** Captures `CURRENT_TIMESTAMP` and `CURRENT_USER` (the PostgreSQL role executing the transaction).

### What the Audit Trigger DOES NOT GUARANTEE (Security Boundaries)
1. **Not Inherently Tamper-Proof:** Triggers record changes, but do not prevent direct manipulation of the audit table itself. A user or role with `UPDATE` or `DELETE` privileges on `portfolio_transaction_audit` can alter or delete audit history. True tamper-resistance requires explicit privilege restrictions:
   ```sql
   -- Production Hardening Recommendation:
   REVOKE UPDATE, DELETE, TRUNCATE ON portfolio_transaction_audit FROM public, app_user_role;
   GRANT SELECT, INSERT ON portfolio_transaction_audit TO app_audit_role;
   ```
2. **Superuser / Owner Bypass:** A database superuser or table owner can disable the trigger (`ALTER TABLE portfolio_transaction DISABLE TRIGGER trg_portfolio_transaction_audit`) or truncate the table (`TRUNCATE portfolio_transaction`), which bypasses per-row triggers.
3. **Application End-User Attribution:** `CURRENT_USER` records the PostgreSQL database role (e.g. `easwarap`). In a production tiered architecture using connection pooling (where all application traffic connects under a shared database role like `app_backend`), `audit_user` will reflect the pool user rather than the individual application end-user, unless the application explicitly passes application session context (e.g. via `SET LOCAL app.user_id = ...`).

---

## 5. System Catalog Verification

Query against `information_schema.triggers` and `pg_trigger`:

```sql
SELECT 
    t.tgname AS trigger_name,
    c.relname AS table_name,
    CASE t.tgenabled 
        WHEN 'O' THEN 'ENABLED (origin and local)'
        WHEN 'D' THEN 'DISABLED'
    END AS status
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'public' AND NOT t.tgisinternal;
```

**Catalog Status:**
```
             trigger_name              |      table_name       |           status           
---------------------------------------+-----------------------+----------------------------
 trg_portfolio_transaction_audit       | portfolio_transaction | ENABLED (origin and local)
 trg_portfolio_transaction_consistency | portfolio_transaction | ENABLED (origin and local)
```

---

## 6. Test Execution and Verification (Task 2 & 4)

### 6.1 Test Suite Structure
- SQL Test Script: [`tests/test_triggers.sql`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/tests/test_triggers.sql)
- Python Runner: [`scripts/test_triggers.py`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/scripts/test_triggers.py)

### 6.2 Executed Tests and Results

| Test # | Test Scenario | Expected Behavior | Actual Result | Status |
| :---: | :--- | :--- | :--- | :---: |
| **1** | Holding of 10 shares, prior SELL of 7 shares, attempted SELL of 5 shares | Rejection with SQLSTATE `22023` (3 shares available, 5 requested) | Caught `22023`, rejected overselling | **PASSED** |
| **2** | Valid SELLs within remaining quantity | Sells of 2 shares and 1 share succeed; subsequent sell of 0.5 shares fails | Successfully sold to 0; excess rejected | **PASSED** |
| **3** | Updating an existing SELL transaction | Updating sell beyond available fails; reducing a sell frees shares for another update | Accounted for freed/allocated shares | **PASSED** |
| **4** | Invalid transaction updates | Rejection of mutations to `transaction_id`, `user_id`, `ticker`, and `transaction_type` | Caught `23514` on all 4 attempts | **PASSED** |
| **5** | Multiple transactions affecting same holding | 3 partial sales of 15 shares (45 total) on 50-share holding; reject 10; sell final 5 | Accurately tracked partial sales | **PASSED** |
| **6** | Integration with `record_stock_purchase` | Procedure increases holding from 10 to 20 shares; sell limit expands from 4 to 14 shares | Seamless integration without double-counting | **PASSED** |
| **7** | Audit logging for INSERT, UPDATE, DELETE | Captures initial state, old/new values on update, and deleted state | Verified full state capture | **PASSED** |
| **8** | Concurrency safety & row locking | Row lock acquired on `portfolio_holding` during validation | Verified row-level lock safety | **PASSED** |
| **Live**| Multi-threaded concurrent race condition | Session 1 sells 7 shares; Session 2 concurrently attempts 5 shares on same holding | Session 1 committed; Session 2 blocked and failed with `22023` | **PASSED** |

### 6.3 Database Cleanliness & Invariance Checks
- **Cleanliness:** Confirmed **0 residual rows** in `app_user`, `portfolio_holding`, `portfolio_transaction`, and `portfolio_transaction_audit`.
- **Market Data Row Counts:**
  - `sector`: 13 rows
  - `company`: 49 rows
  - `daily_price_history`: 287,310 rows
  - `corporate_action`: 1,653 rows
  - `current_fundamentals`: 49 rows
  - `stock_summary`: 49 rows
- **Analytical SQL Query Regression:** Executed [`scripts/test_queries.py`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/scripts/test_queries.py): **10/10 files passed (50 queries, 0 failures)**.
