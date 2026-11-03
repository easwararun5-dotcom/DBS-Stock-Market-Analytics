# CSV Ingestion Plan & Execution Report

**Project:** DBS – Stock Market Analytics and Portfolio Management System  
**Database:** `stock_market_db` (PostgreSQL 18.4, `localhost:5435`, user: `easwarap`)  
**Execution Status:** **EXECUTED & FULLY VERIFIED**  
**Execution Timestamp:** 2026-10-19T12:56:18+05:30  
**Pipeline Script:** [`scripts/ingest_data.py`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics/scripts/ingest_data.py)

---

## 1. Execution Summary

The CSV ingestion pipeline was executed inside an atomic transaction using native PostgreSQL `COPY ... FROM STDIN`. The entire load of 288,963 financial data records was completed in **1.52 seconds**.

```bash
# Execution Command:
python3 scripts/ingest_data.py --host localhost --port 5435 --dbname stock_market_db --user easwarap
```

---

## 2. Table Record Count Verification

All 13 tables in `stock_market_db` were verified post-ingestion:

| Table Name | Actual Count | Expected Count | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **`sector`** | **13** | 13 | **PASSED** | Exactly 13 distinct industry sectors populated. |
| **`company`** | **49** | 49 | **PASSED** | 49 Nifty 50 constituents with foreign keys to `sector`. |
| **`daily_price_history`** | **287,310** | 287,310 | **PASSED** | 100% of historical price rows (1999–2026) loaded. |
| **`corporate_action`** | **1,653** | 1,653 | **PASSED** | 1,555 dividends + 98 stock splits (10 multi-action dates). |
| **`current_fundamentals`** | **49** | 49 | **PASSED** | Latest snapshot (2026-01-30) for each of the 49 companies. |
| **`stock_summary`** | **49** | 49 | **PASSED** | All 16 summary statistics mapped from processed CSV. |
| **`app_user`** | **0** | 0 | **PASSED** | Zero fabricated application records. |
| **`user_watchlist`** | **0** | 0 | **PASSED** | Zero fabricated application records. |
| **`portfolio_holding`** | **0** | 0 | **PASSED** | Zero fabricated application records. |
| **`portfolio_transaction`** | **0** | 0 | **PASSED** | Zero fabricated application records. |
| **`alert`** | **0** | 0 | **PASSED** | Zero fabricated application records. |
| **`portfolio_risk_analysis`** | **0** | 0 | **PASSED** | Zero fabricated application records. |
| **`ml_prediction`** | **0** | 0 | **PASSED** | Zero fabricated application records. |

---

## 3. Data Integrity & Validation Query Results

### A. Foreign-Key Referential Integrity (0 Orphaned Records)
```sql
SELECT count(*) FROM daily_price_history p LEFT JOIN company c ON p.ticker = c.ticker WHERE c.ticker IS NULL; -- 0
SELECT count(*) FROM corporate_action a LEFT JOIN company c ON a.ticker = c.ticker WHERE c.ticker IS NULL;      -- 0
SELECT count(*) FROM current_fundamentals f LEFT JOIN company c ON f.ticker = c.ticker WHERE c.ticker IS NULL; -- 0
SELECT count(*) FROM stock_summary s LEFT JOIN company c ON s.ticker = c.ticker WHERE c.ticker IS NULL;         -- 0
SELECT count(*) FROM company c LEFT JOIN sector s ON c.sector_id = s.sector_id WHERE s.sector_id IS NULL;       -- 0
```
* **Result:** **PASSED**. Zero orphaned records across all tables.

### B. Uniqueness Constraints
* `(ticker, trading_date)` in `daily_price_history`: **0 duplicates**.
* `(ticker, action_date, action_type)` in `corporate_action`: **0 duplicates**.

### C. Negative Historical Price Preservation
* Negative close prices for `ADANIENT.NS`: Exactly **47 trading days** (2002-07-01 to 2002-09-03) preserved with values ranging from `-0.0122` to `-0.0107`.
* Total negative close prices across entire database: Exactly **47 rows** (all belonging to `ADANIENT.NS`).

### D. Missing Fundamentals Policy
* All-NULL `peg_ratio`: Exactly **49 of 49 rows** are `NULL`.
* `INDUSINDBK.NS`: `pe_ratio` is **NULL**; `dividend_yield` is **NULL**.
* `COALINDIA.NS`: `beta` is **NULL**.
* Derived snapshot year: `fiscal_year = 2026` across all 49 rows.
