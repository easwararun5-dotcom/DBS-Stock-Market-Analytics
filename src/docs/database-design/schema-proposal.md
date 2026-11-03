# Database Design Proposal (Audited & Verified Specification)

**Project:** DBS – Stock Market Analytics and Portfolio Management System  
**Database:** `stock_market_db` (PostgreSQL 18.4, `localhost:5435`, user: `easwarap`)  
**Status:** Pre-Implementation Audited Specification (Strict ER Diagram & Dataset Alignment)

---

## 1. Executive Summary & Audited Dataset Scope

Visual inspection of all three hand-drawn ER diagram sheets (`docs/er-diagram/`) and a full read-only audit of both CSV files (`nifty50_historical_data.csv` and `nifty50_summary_statistics.csv`) has been completed:

* **Company Scope (49 Tickers):** Both CSV files contain exactly **49 distinct tickers** (100% mutual match). The dataset represents 49 active constituents of the Nifty 50 index (one constituent was omitted during source dataset compilation). All expected counts are calibrated to 49 companies.
* **Sector Scope (13 Sectors):** Both CSV files map all 49 companies into exactly **13 distinct industry sectors**.
* **Corporate Actions Scope (1,653 Events):** Exactly 1,555 dividend records and 98 stock split records, including 10 dates where both occurred simultaneously.
* **Price History Scope (287,310 Records):** Validated across all 49 tickers from 1999 to 2026.

---

## 2. Audited Resolutions to Core Schema Questions

### A. PORTFOLIO_RISK_ANALYSIS: "transaction" is an Attribute, Not a Relationship
* **ER Diagram Evidence:** On Sheet 2, `PORTFOLIO_RISK_ANALYSIS` is an entity rectangle connected to `APP_USER` via the `HAS` relationship diamond (1 `APP_USER` : N `PORTFOLIO_RISK_ANALYSIS`). Attached to `PORTFOLIO_RISK_ANALYSIS` are 6 attribute ovals: `analysis_id` (PK), `sharpe_ratio`, `volatility`, `max_drawdown`, `Sector_concentration`, and `transaction`.
* **Resolution:** The shape labeled `transaction` is an **oval (attribute)**, not a relationship diamond. Furthermore, risk analysis is calculated across an entire portfolio of holdings, not a single individual trade. To avoid inventing an unsupported foreign key, it is modeled as an attribute:
  - Column: `transaction_context TEXT`
  - Description: Captures transaction notes, turnover window, or trade batch identifier evaluated during the risk analysis run. No foreign key to `portfolio_transaction` is created.

### B. Prevention of Inconsistent Portfolio Ownership
* **Cross-User Holding Isolation:** In the initial model, `portfolio_transaction` had separate foreign keys to `portfolio_holding(holding_id)` and `app_user(user_id)`. This permitted a transaction by User A to reference a holding owned by User B.
* **Relational Solution:**
  1. In `portfolio_holding`: add `CONSTRAINT uq_holding_user UNIQUE (holding_id, user_id)`.
  2. In `portfolio_transaction`: enforce `CONSTRAINT fk_transaction_holding_user FOREIGN KEY (holding_id, user_id) REFERENCES portfolio_holding(holding_id, user_id) ON DELETE SET NULL`.
  This guarantees that a user can never link transactions to holdings owned by another user.

### C. CURRENT_FUNDAMENTALS: Uniform Snapshot Policy & Missing Value Handling
* **Uniform Snapshot Date:** Across all 49 tickers in `nifty50_historical_data.csv`, the maximum date is uniformly **`2026-01-30`**. No dates are mixed.
* **Static Nature of Fundamentals:** Data audit reveals fundamentals in the historical CSV are constant across all dates for each ticker.
* **Missing Value Policy:**
  - `peg_ratio NUMERIC(10,4)` is 100% empty across the entire dataset; stored as SQL `NULL`.
  - `INDUSINDBK.NS` is missing `pe_ratio` and `dividend_yield`; stored as SQL `NULL`.
  - `COALINDIA.NS` is missing `beta`; stored as SQL `NULL`.
  - Missing source metrics are preserved as `NULL` without forward-filling or fabricating values.
* **Derived Snapshot Year (`fiscal_year`):** Derived uniformly as `2026` (`EXTRACT(YEAR FROM max_date)`), explicitly documented as a derived snapshot year.
* **Dataset Extensions:** `market_cap` and `peg_ratio` are retained to avoid data loss from the CSV, documented in table comments as extensions beyond the 7 ER diagram attributes.

### D. Origin of Negative Adjusted Prices
* **Source Trace:** In `nifty50_historical_data.csv`, exactly 47 rows for `ADANIENT.NS` (2002-07-01 to 2002-09-03) have negative prices (-0.0122 to -0.0107).
* **Explanation:** On 2002-09-04, `ADANIENT.NS` paid a dividend of ₹1.45. Prior to this date, the stock had split multiple times (cumulative split factor of 1:10, 1:2, etc.), reducing the nominal share price to ~₹0.05. Yahoo Finance's backward adjustment subtracts dividend payments from past prices, which produced negative split-adjusted prices (-0.0122). In `nifty50_summary_statistics.csv`, `Starting_Price` is `-0.0122`, `Lowest_Price` is `-0.0124`, and `Total_Return_%` is `-16,597,489.4155%`.
* **Constraint Recommendation:** To preserve historical source records unaltered without ingestion failure, price check constraints (`CHECK >= 0`) are omitted on price columns in `daily_price_history` and `stock_summary`.

### E. Corporate Action Integrity
* Exactly 1,555 dividends and 98 splits (1,653 total events) are extracted.
* Exactly 10 rows have both a dividend and split on the same date, generating two distinct, valid rows.
* Guaranteed event uniqueness via `CONSTRAINT uq_corp_action UNIQUE (ticker, action_date, action_type)`.

---

## 3. Relational Table Specifications

| Table | Columns (Data Type & Constraints) | Primary Key | Foreign Keys | Relationship / Cardinality |
| :--- | :--- | :--- | :--- | :--- |
| **`sector`** | `sector_id` SERIAL,<br>`sector_name` TEXT NOT NULL UNIQUE | `sector_id` | – | 1 : N to `company` (13 sectors) |
| **`company`** | `ticker` TEXT,<br>`company_name` TEXT NOT NULL,<br>`sector_id` INT NOT NULL | `ticker` | `sector_id` → `sector(sector_id)` ON DELETE RESTRICT | N : 1 from `sector`, 1 : N to market entities (49 companies) |
| **`daily_price_history`** | `ticker` TEXT NOT NULL,<br>`trading_date` DATE NOT NULL,<br>`open_price` NUMERIC(14,4),<br>`high_price` NUMERIC(14,4),<br>`low_price` NUMERIC(14,4),<br>`close_price` NUMERIC(14,4),<br>`volume` BIGINT CHECK (`volume` >= 0),<br>`daily_return` NUMERIC(10,4),<br>`vol_20d` NUMERIC(10,4),<br>`ma_50` NUMERIC(14,4),<br>`ma_200` NUMERIC(14,4) | Composite: (`ticker`, `trading_date`) | `ticker` → `company(ticker)` ON DELETE CASCADE | 1 `company` : N `daily_price_history` (287,310 rows) |
| **`corporate_action`** | `action_id` SERIAL,<br>`ticker` TEXT NOT NULL,<br>`action_date` DATE NOT NULL,<br>`action_type` TEXT NOT NULL CHECK (`action_type` IN ('Dividend', 'Stock_Split')),<br>`action_value` NUMERIC(14,4) NOT NULL CHECK (`action_value` > 0),<br>CONSTRAINT `uq_corp_action` UNIQUE (`ticker`, `action_date`, `action_type`) | `action_id` | `ticker` → `company(ticker)` ON DELETE CASCADE | 1 `company` : N `corporate_action` (1,653 rows) |
| **`current_fundamentals`** | `ticker` TEXT,<br>`pe_ratio` NUMERIC(10,4),<br>`forward_pe` NUMERIC(10,4),<br>`price_to_book` NUMERIC(10,4),<br>`dividend_yield` NUMERIC(10,4),<br>`eps` NUMERIC(14,4),<br>`beta` NUMERIC(10,4),<br>`fiscal_year` INT,<br>`market_cap` NUMERIC(22,2),<br>`peg_ratio` NUMERIC(10,4),<br>`last_updated` DATE NOT NULL DEFAULT CURRENT_DATE | `ticker` | `ticker` → `company(ticker)` ON DELETE CASCADE | 1 `company` : 1 `current_fundamentals` (49 rows) |
| **`stock_summary`** | `ticker` TEXT,<br>`first_trading_date` DATE NOT NULL,<br>`last_trading_date` DATE NOT NULL,<br>`total_trading_days` INT NOT NULL CHECK (`total_trading_days` > 0),<br>`starting_price` NUMERIC(16,4),<br>`ending_price` NUMERIC(16,4),<br>`total_return_pct` NUMERIC(18,4),<br>`highest_price` NUMERIC(16,4),<br>`lowest_price` NUMERIC(16,4),<br>`avg_daily_volume` NUMERIC(18,2),<br>`total_dividends_paid` NUMERIC(16,4),<br>`number_of_splits` INT NOT NULL DEFAULT 0 CHECK (`number_of_splits` >= 0),<br>`avg_daily_return_pct` NUMERIC(10,4),<br>`volatility_pct` NUMERIC(10,4),<br>`current_market_cap` NUMERIC(22,2),<br>`current_pe_ratio` NUMERIC(10,4) | `ticker` | `ticker` → `company(ticker)` ON DELETE CASCADE | 1 `company` : 1 `stock_summary` (49 rows) |
| **`app_user`** | `user_id` SERIAL,<br>`username` TEXT NOT NULL UNIQUE,<br>`email` TEXT NOT NULL UNIQUE,<br>`password_hash` TEXT NOT NULL,<br>`role` TEXT NOT NULL CHECK (`role` IN ('admin', 'user')),<br>`created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | `user_id` | – | 1 : N to user modules |
| **`user_watchlist`** | `watchlist_id` SERIAL,<br>`user_id` INT NOT NULL,<br>`ticker` TEXT NOT NULL,<br>`alert_price` NUMERIC(14,4),<br>`added_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,<br>CONSTRAINT `uq_user_ticker` UNIQUE (`user_id`, `ticker`) | `watchlist_id` | `user_id` → `app_user(user_id)` ON DELETE CASCADE,<br>`ticker` → `company(ticker)` ON DELETE CASCADE | N : N resolution between `app_user` and `company` |
| **`portfolio_holding`** | `holding_id` SERIAL,<br>`user_id` INT NOT NULL,<br>`ticker` TEXT NOT NULL,<br>`quantity` NUMERIC(20,4) NOT NULL CHECK (`quantity` >= 0),<br>`invested_value` NUMERIC(22,2) NOT NULL CHECK (`invested_value` >= 0),<br>`average_buy_price` NUMERIC(14,4) NOT NULL CHECK (`average_buy_price` >= 0),<br>`purchase_date` DATE NOT NULL,<br>CONSTRAINT `uq_holding_user` UNIQUE (`holding_id`, `user_id`) | `holding_id` | `user_id` → `app_user(user_id)` ON DELETE CASCADE,<br>`ticker` → `company(ticker)` ON DELETE RESTRICT | 1 `app_user` : N `portfolio_holding` |
| **`portfolio_transaction`** | `transaction_id` SERIAL,<br>`holding_id` INT,<br>`user_id` INT NOT NULL,<br>`ticker` TEXT NOT NULL,<br>`transaction_type` TEXT NOT NULL CHECK (`transaction_type` IN ('BUY', 'SELL', 'DIVIDEND', 'SPLIT')),<br>`transaction_date` DATE NOT NULL,<br>`price` NUMERIC(14,4) NOT NULL CHECK (`price` >= 0),<br>`quantity` NUMERIC(20,4) NOT NULL CHECK (`quantity` > 0),<br>CONSTRAINT `fk_transaction_holding_user` FOREIGN KEY (`holding_id`, `user_id`) REFERENCES `portfolio_holding`(`holding_id`, `user_id`) ON DELETE SET NULL (`holding_id`) | `transaction_id` | `(holding_id, user_id)` → `portfolio_holding(holding_id, user_id)` ON DELETE SET NULL (`holding_id`),<br>`user_id` → `app_user(user_id)` ON DELETE CASCADE,<br>`ticker` → `company(ticker)` ON DELETE RESTRICT | 1 `holding` : N `transaction`, 1 `user` : N `transaction` |
| **`alert`** | `alert_id` SERIAL,<br>`user_id` INT NOT NULL,<br>`ticker` TEXT NOT NULL,<br>`alert_type` TEXT NOT NULL,<br>`alert_message` TEXT NOT NULL,<br>`status` TEXT NOT NULL CHECK (`status` IN ('ACTIVE', 'READ', 'DISMISSED')),<br>`triggered_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | `alert_id` | `user_id` → `app_user(user_id)` ON DELETE CASCADE,<br>`ticker` → `company(ticker)` ON DELETE CASCADE | 1 `company` : N `alert` (`GENERATES`),<br>1 `user` : N `alert` (`RECEIVE`) |
| **`portfolio_risk_analysis`** | `analysis_id` SERIAL,<br>`user_id` INT NOT NULL,<br>`analysis_date` DATE NOT NULL DEFAULT CURRENT_DATE,<br>`sharpe_ratio` NUMERIC(10,4),<br>`volatility` NUMERIC(10,4),<br>`max_drawdown` NUMERIC(10,4),<br>`sector_concentration` JSONB,<br>`transaction_context` TEXT | `analysis_id` | `user_id` → `app_user(user_id)` ON DELETE CASCADE | 1 `app_user` : N `portfolio_risk_analysis` |
| **`ml_prediction`** | `prediction_id` SERIAL,<br>`ticker` TEXT NOT NULL,<br>`prediction_date` DATE NOT NULL,<br>`forecast_horizon` INT NOT NULL CHECK (`forecast_horizon` > 0),<br>`predicted_price` NUMERIC(14,4) NOT NULL,<br>`confidence_score` NUMERIC(6,4) CHECK (`confidence_score` BETWEEN 0 AND 1),<br>`model_name` TEXT NOT NULL,<br>`created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | `prediction_id` | `ticker` → `company(ticker)` ON DELETE CASCADE | 1 `company` : N `ml_prediction` |

---

## 4. Foreign Key Index Strategy

```sql
CREATE INDEX idx_company_sector_id ON company(sector_id);
CREATE INDEX idx_price_ticker ON daily_price_history(ticker);
CREATE INDEX idx_price_date ON daily_price_history(trading_date);
CREATE INDEX idx_corp_action_ticker ON corporate_action(ticker);
CREATE INDEX idx_corp_action_date ON corporate_action(action_date);
CREATE INDEX idx_watchlist_user ON user_watchlist(user_id);
CREATE INDEX idx_watchlist_ticker ON user_watchlist(ticker);
CREATE INDEX idx_holding_user ON portfolio_holding(user_id);
CREATE INDEX idx_holding_ticker ON portfolio_holding(ticker);
CREATE INDEX idx_transaction_holding_user ON portfolio_transaction(holding_id, user_id);
CREATE INDEX idx_transaction_user ON portfolio_transaction(user_id);
CREATE INDEX idx_transaction_ticker ON portfolio_transaction(ticker);
CREATE INDEX idx_alert_user ON alert(user_id);
CREATE INDEX idx_alert_ticker ON alert(ticker);
CREATE INDEX idx_risk_user ON portfolio_risk_analysis(user_id);
CREATE INDEX idx_prediction_ticker ON ml_prediction(ticker);
```
