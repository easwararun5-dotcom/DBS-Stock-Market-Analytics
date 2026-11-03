# Academic Database Normalization Audit & Specification Report
**Project:** DBS Stock Market Analytics and Portfolio Management System  
**Audited Databases:** 
- PostgreSQL 18.4 (`stock_market_db` on port 5435)
- TimescaleDB / PostgreSQL 17.11 (`stock_timescale_db` on port 5434)  
**Deliverable Status:** Formally Audited DBMS Project Submission Specification  
**Scope:** Complete Academic Normalization Lifecycle (Raw Datasets $\to$ Relational Schema) & Application Schema Normalization (Migration 05)

---

## 1. Project Overview & System Architecture

The DBS Stock Market Analytics and Portfolio Management System is an end-to-end relational financial intelligence platform supporting equity analytics, portfolio management, risk evaluation, and paper trading for Nifty 50 constituent companies.

The system is architected across a **Dual-Database Boundary**:
1. **Relational Core (PostgreSQL 18.4 on Port 5435, `stock_market_db`):** Houses master taxonomies, listed corporate entities, corporate actions, fundamental snapshots, analytical rollups, user accounts, watchlists, virtual cash portfolios, paper-trading transaction ledgers, and portfolio risk analyses. Enforces declarative referential integrity, domain check constraints, transactional triggers, and normal-form invariants.
2. **Time-Series Engine (TimescaleDB on Port 5434, `stock_timescale_db`):** Houses partitioned hypertables (28 chunks across 360-day intervals) dedicated to high-frequency historical OHLCV chart queries and native `time_bucket()` aggregations. Operates without cross-database foreign key constraints.

### 1.1 Structural Separation of Normalization Phases
To ensure academic rigor, this report explicitly separates two distinct normalization phases:
- **Part A: Raw Dataset Normalization:** The decomposition of the external raw market datasets (`nifty50_historical_data.csv` and `nifty50_summary_statistics.csv`) into relational core tables during ingestion and schema design.
- **Part B: PostgreSQL Application Schema Normalization (Migration 05):** The subsequent operational refactoring of the application schema to eliminate higher-normal-form violations in portfolio holdings and non-atomic JSONB structures in portfolio risk analytics.

---

## PART A: RAW DATASET NORMALIZATION

## 2. Original Raw Datasets

The raw market data originates from Yahoo Finance and is stored in two primary files within `data/`:

### 2.1 Primary Historical Dataset: `data/historical/nifty50_historical_data.csv`
- **Physical Size:** 87,715,220 bytes (~87.7 MB)
- **Record Count:** Exactly 287,310 rows × 25 columns.
- **Coverage Period:** January 1, 1999 to January 30, 2026 (27 years of daily trading history).
- **Entities Covered:** Exactly 49 listed equity tickers across 13 industrial sectors (one stock omitted by the provider during collection).
- **Physical Format:** Plain-text comma-separated values (CSV) with UTF-8 encoding. Every line represents a scalar-delimited tuple containing price observations, rolling technical indicators, static corporate attributes, and snapshot valuation metrics.

### 2.2 Secondary Summary Statistics Dataset: `data/processed/nifty50_summary_statistics.csv`
- **Physical Size:** 13,731 bytes (~13.7 KB)
- **Record Count:** Exactly 49 rows × 18 columns (exactly 1 row per company).
- **Provenance & Nature:** Precomputed statistical rollup produced by offline processing. Contains lifetime performance aggregates (all-time high/low, annualized volatility, lifetime dividends, split counts, starting/ending prices).
- **Ingestion Target:** Directly imported into base table `stock_summary` as an analytical reporting cache.

### 2.3 Metadata Specification: `data/metadata/metadata.json`
- **Recorded Attributes:** Documents the 25-year scope, collection timestamp (`2026-01-31 07:42:00`), 49 constituent companies, and the 13 verified sectors: *Automobile, Cement, Consumer Durables, Energy, FMCG, Financials, Healthcare, IT, Infrastructure, Metals, Pharma, Power, Telecom*.

---

## 3. Original Attributes, Candidate Keys, and Functional Dependencies

### 3.1 Column Classification of `nifty50_historical_data.csv` (25 Columns)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      25 RAW HISTORICAL CSV ATTRIBUTES BY DOMAIN                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Identification & Classification (4):                                                │
│    Date, Ticker, Company_Name, Sector                                                  │
│ 2. Daily Trading Session OHLCV (5):                                                    │
│    Open, High, Low, Close, Volume                                                      │
│ 3. Corporate Actions (2):                                                              │
│    Dividend, Stock_Split                                                               │
│ 4. Rolling Technical & Return Indicators (4):                                          │
│    Daily_Return, Volatility_20D, MA_50, MA_200                                         │
│ 5. Fundamental Valuation Snapshots (10):                                               │
│    Market_Cap, PE_Ratio, Forward_PE, PEG_Ratio, Price_to_Book, Dividend_Yield,         │
│    EPS, Beta, 52Week_High, 52Week_Low                                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Candidate Key Verification

We executed reproducible verification checks across all 287,310 records of `nifty50_historical_data.csv`:
- **Single Attribute Uniqueness:**
  - `Date`: Repeats up to 49 times per trading session $\to$ **Not unique**.
  - `Ticker`: Repeats between 2,027 and 6,770 times per company $\to$ **Not unique**.
- **Composite Pair $\{\text{Ticker}, \text{Date}\}$:**
  $$\text{Total Records} = 287,310 \quad|\quad \text{Distinct } \{\text{Ticker}, \text{Date}\} = 287,310 \quad|\quad \text{Duplicate Pairs} = 0$$

**Mathematical Conclusion:**
Because $\{\text{Ticker}, \text{Date}\}$ is irreducible (neither $\text{Ticker}$ nor $\text{Date}$ alone determines the tuple) and uniquely identifies every record in the relation, $\{\text{Ticker}, \text{Date}\}$ is the **sole minimal Candidate Key** of the raw relation $R_{\text{raw}}$:
$$\text{Candidate Key}(R_{\text{raw}}) = \{\text{Ticker}, \text{Date}\}$$

### 3.3 Functional Dependencies Established from the Dataset

Empirical testing across the entire 287,310 tuples establishes the following non-trivial functional dependencies:

1. **Full Functional Dependencies on Candidate Key:**
   $$FD_1: \{\text{Ticker}, \text{Date}\} \to \{\text{Open}, \text{High}, \text{Low}, \text{Close}, \text{Volume}\}$$
   $$FD_2: \{\text{Ticker}, \text{Date}\} \to \{\text{Daily\_Return}, \text{Volatility\_20D}, \text{MA\_50}, \text{MA\_200}\}$$
   *Proof:* For every specific ticker on a specific trading session, there exists exactly one recorded set of OHLCV prices and rolling indicators.

2. **Partial Functional Dependencies on Subset $\text{Ticker}$ (2NF Violations):**
   $$FD_3: \text{Ticker} \to \{\text{Company\_Name}, \text{Sector}\}$$
   *Proof:* Tested across all 287,310 rows. Zero tickers map to more than one company name or sector. Exactly 49 unique tickers map to 49 unique company names and 13 distinct sectors.
   $$FD_4: \text{Ticker} \to \{\text{Market\_Cap}, \text{PE\_Ratio}, \text{Forward\_PE}, \text{Price\_to\_Book}, \text{Dividend\_Yield}, \text{EPS}, \text{Beta}, \text{52Week\_High}, \text{52Week\_Low}\}$$
   *Proof:* In the raw CSV dataset, these fundamental metrics are static snapshot constants repeated identically across every historical date for each ticker (variance across dates = 0). `PEG_Ratio` is 100% NULL across all 287,310 records.

3. **Transitive Functional Dependencies (3NF Violations):**
   $$FD_5: \text{Ticker} \to \text{Sector\_ID} \quad\text{and}\quad \text{Sector\_ID} \to \text{Sector\_Name}$$
   *Proof:* Multiple tickers share identical sector names (e.g., `Financials` has 53,903 rows across multiple banks). In a relation keyed by $\text{Ticker}$, $\text{Ticker} \to \text{Sector\_ID} \to \text{Sector\_Name}$ is a transitive dependency where $\text{Sector\_ID}$ is not a candidate key.

4. **Discrete Event Functional Dependency:**
   $$FD_6: \{\text{Ticker}, \text{Date}, \text{Action\_Type}\} \to \text{Action\_Value}$$
   *Proof:* In the historical data, a company occasionally issues both a cash dividend and a stock split on the exact same date (observed on 10 dates, e.g., `TCS.NS` on 2006-07-28). Thus, $\text{Action\_Type}$ is necessary to determine the scalar event value.

---

## 4. Starting Normal-Form Assessment

### 4.1 Primary Historical Dataset (`nifty50_historical_data.csv`)
An essential academic principle must be stated:
> **A flat CSV file whose cells contain scalar, atomic values does NOT violate First Normal Form (1NF) merely because company names or sector labels repeat.**

- **Domain Atomicity:** Every field in `nifty50_historical_data.csv` contains an indivisible scalar value from its domain (e.g., IEEE floating-point numbers, integers, ISO timestamps, or text strings). There are no comma-separated lists, JSON objects, nested relations, or repeating attribute groups within any single row.
- **Tuple Distinctness:** Every row is distinct, uniquely identified by the composite candidate key $\{\text{Ticker}, \text{Date}\}$.
- **Evaluation:** The raw historical relation $R_{\text{raw}}$ **already satisfies First Normal Form (1NF)**.
- **Misconception Corrected:** Repeated company names (`'Axis Bank Ltd.'` appearing 6,767 times) or sector labels (`'Financials'` appearing 53,903 times) do **not** violate 1NF. They violate **Second Normal Form (2NF)** (due to partial dependencies on a composite key) and **Third Normal Form (3NF)** (due to transitive dependencies).

### 4.2 Secondary Summary Statistics Dataset (`nifty50_summary_statistics.csv`)
- **Dimensions:** Exactly 49 rows × 18 columns.
- **Domain Atomicity:** Every cell contains a single scalar value. Meets **1NF**.
- **Candidate Key:** `Ticker` is the verified candidate key (all 49 rows have unique tickers).
- **2NF Assessment:** Under formal relational theory, a partial functional dependency requires a proper subset of a composite candidate key. Because `Ticker` is a single attribute with no non-empty proper subsets, partial dependencies cannot exist. Therefore, `nifty50_summary_statistics.csv` **satisfies 2NF**.
- **3NF and BCNF Assessment & Required Assumptions:**
  - If the schema's enforced functional dependencies are defined strictly as $F = \{\text{Ticker} \to \text{all other 17 attributes}\}$, then because `Ticker` is a candidate key, every determinant in $F$ is a superkey. Under this minimal functional dependency model, the relation satisfies **3NF and BCNF**.
  - **Explicit Caveat & Assumption:** Assigning 3NF/BCNF holds only if the algebraic formula defining $\text{Total\_Return\_%}$ from $\text{Starting\_Price}$ and $\text{Ending\_Price}$, and the duplication of `Current_Market_Cap` and `Current_PE_Ratio` from `current_fundamentals`, are treated as computational derivation rules rather than schema-enforced non-key functional dependencies.
  - If one formally posits the inter-attribute constraint $\{\text{Starting\_Price}, \text{Ending\_Price}\} \to \text{Total\_Return\_%}$ as an integrity constraint in $F$, then $\{\text{Starting\_Price}, \text{Ending\_Price}\}$ is a determinant that is not a candidate key, which would violate 3NF.
  - In DBMS engineering practice, `stock_summary` is designed as an **analytical reporting rollup / summary cache** that trades computational normalization for zero-join dashboard query performance.

---

## 5. Unnormalized Form (UNF) & 1NF Analysis

### 5.1 Conceptual Unnormalized Form (UNF)
Before tabular flattening, stock market data conceptually exists in an **Unnormalized Form (UNF)** as a hierarchical object document:

$$\text{UNF\_STOCK} = \Big( \underline{\text{Ticker}}, \text{Company\_Name}, \text{Sector}, \text{Fundamentals}(\dots), \{\text{Date}, \text{Open}, \text{High}, \text{Low}, \text{Close}, \text{Volume}, \dots\}^*, \{\text{Action\_Date}, \text{Action\_Type}, \text{Action\_Value}\}^* \Big)$$

In this conceptual representation:
- Daily trading history $\{\text{Date}, \text{Open}, \dots\}^*$ is a **repeating group** nested within each company.
- Corporate actions $\{\text{Action\_Date}, \dots\}^*$ represent a second **repeating group**.
- Flattening this conceptual hierarchy into a single two-dimensional table by replicating company attributes across every trading session yields the 287,310-row flat 1NF relation $R_{\text{raw}}$.

### 5.2 Application-Level 1NF Violation in `portfolio_risk_analysis`
In contrast to the market CSV, the application schema prior to Migration 05 contained a **genuine 1NF violation**:
- Column `portfolio_risk_analysis.sector_concentration` stored non-atomic JSONB objects:
  $$\text{"sector\_concentration"}: \{"\text{IT}": 54.55, "\text{Energy}": 45.45\}$$
- Because JSONB stores an unstructured key-value collection inside a single column, it violated scalar atomicity. This was decomposed in Migration 05 into the atomic child relation `portfolio_risk_sector_allocation`.

---

## 6. Second Normal Form (2NF) Decomposition

### 6.1 Formal Definition of 2NF
A relation $R$ is in **Second Normal Form (2NF)** if and only if:
1. $R$ satisfies 1NF.
2. Every non-prime attribute $A \in (R \setminus \text{Key})$ is **fully functionally dependent** on every candidate key $K$ of $R$.
3. No non-prime attribute may depend on a proper subset of any composite candidate key (i.e., **no partial functional dependencies**).

### 6.2 Partial Dependencies in $R_{\text{raw}}$
Given Candidate Key $K = \{\text{Ticker}, \text{Date}\}$:
- $\text{Ticker} \to \{\text{Company\_Name}, \text{Sector}\}$ ($FD_3$) depends strictly on proper subset $\text{Ticker}$.
- $\text{Ticker} \to \text{Fundamentals}$ ($FD_4$) depends strictly on proper subset $\text{Ticker}$.
- Corporate actions (`Dividend`, `Stock_Split`) are discrete events that occur on fewer than $0.6\%$ of trading dates.

### 6.3 2NF Decomposition Step
To eliminate partial dependencies, $R_{\text{raw}}$ is decomposed into vertical components:

1. **`daily_price_history`:**
   $$\text{DAILY\_PRICE\_HISTORY}(\underline{\text{Ticker}, \text{Trading\_Date}}, \text{Open\_Price}, \text{High\_Price}, \text{Low\_Price}, \text{Close\_Price}, \text{Volume}, \text{Daily\_Return}, \text{Vol\_20D}, \text{MA\_50}, \text{MA\_200})$$
   - Candidate Key: $\{\text{Ticker}, \text{Trading\_Date}\}$.
   - All non-prime attributes require both $\text{Ticker}$ and $\text{Trading\_Date}$. Fully dependent $\to$ **Satisfies 2NF**.

2. **`company_raw`:**
   $$\text{COMPANY\_RAW}(\underline{\text{Ticker}}, \text{Company\_Name}, \text{Sector})$$
   - Candidate Key: $\text{Ticker}$. Single-attribute key $\to$ **Automatically satisfies 2NF**.

3. **`current_fundamentals`:**
   $$\text{CURRENT\_FUNDAMENTALS}(\underline{\text{Ticker}}, \text{PE\_Ratio}, \text{Forward\_PE}, \text{Price\_to\_Book}, \text{Dividend\_Yield}, \text{EPS}, \text{Beta}, \text{Fiscal\_Year}, \text{Market\_Cap}, \text{PEG\_Ratio}, \text{Last\_Updated})$$
   - Candidate Key: $\text{Ticker}$. Single-attribute key $\to$ **Automatically satisfies 2NF**.

---

## 7. Third Normal Form (3NF) Decomposition

### 7.1 Formal Definition of 3NF
A relation $R$ is in **Third Normal Form (3NF)** if and only if:
1. $R$ satisfies 2NF.
2. For every non-trivial functional dependency $X \to Y$ holding in $R$:
   - $X$ is a **superkey** of $R$, OR
   - Every attribute $A \in Y$ is a **prime attribute** (a member of some candidate key of $R$).
3. In short: **no non-prime attribute is transitively dependent on any candidate key**.

### 7.2 Transitive Dependency in `COMPANY_RAW`
In $\text{COMPANY\_RAW}(\underline{\text{Ticker}}, \text{Company\_Name}, \text{Sector})$:
- Candidate Key: $\text{Ticker}$.
- Functional dependencies:
  $$\text{Ticker} \to \text{Sector\_Name}$$
  $$\text{Sector\_Name} \not\to \text{Ticker} \quad (\text{Multiple companies share identical sector names})$$
- Introducing a normalized sector entity with surrogate key $\text{Sector\_ID}$:
  $$\text{Ticker} \to \text{Sector\_ID} \to \text{Sector\_Name}$$
- Because $\text{Sector\_ID}$ is not a superkey of $\text{COMPANY\_RAW}$ and $\text{Sector\_Name}$ is a non-prime attribute, $\text{Ticker} \to \text{Sector\_Name}$ is a **transitive dependency violating 3NF**.

### 7.3 3NF Decomposition of `COMPANY_RAW`
Decompose $\text{COMPANY\_RAW}$ into two 3NF relations:

1. **`sector`:**
   $$\text{SECTOR}(\underline{\text{Sector\_ID}}, \text{Sector\_Name})$$
   - Candidate Keys: $\text{Sector\_ID}$ (Enforced PK), $\text{Sector\_Name}$ (Enforced UNIQUE).
   - All determinants are superkeys $\to$ **Satisfies 3NF**.

2. **`company`:**
   $$\text{COMPANY}(\underline{\text{Ticker}}, \text{Company\_Name}, \text{Sector\_ID})$$
   - Candidate Key: $\text{Ticker}$ (Enforced PK).
   - Foreign Key: $\text{Sector\_ID} \text{ REFERENCES } \text{sector}(\text{Sector\_ID})$.
   - Transitive dependency eliminated $\to$ **Satisfies 3NF**.

---

## 8. Boyce-Codd Normal Form (BCNF) Assessment

### 8.1 Formal Definition of BCNF
A relation $R$ is in **Boyce-Codd Normal Form (BCNF)** if and only if for every non-trivial functional dependency $X \to Y$ holding in $R$, $X$ is a **superkey** of $R$. BCNF eliminates all update anomalies arising from functional dependencies, including those where a determinant is part of a composite candidate key.

### 8.2 Academic Assessment Across All Decomposed Relations

1. **`sector` $(\underline{\text{Sector\_ID}}, \text{Sector\_Name})$:**
   - Non-trivial FDs: $\text{Sector\_ID} \to \text{Sector\_Name}$ and $\text{Sector\_Name} \to \text{Sector\_ID}$.
   - Both $\text{Sector\_ID}$ and $\text{Sector\_Name}$ are candidate keys (enforced via PK and UNIQUE).
   - Every determinant is a superkey $\implies$ **Strictly satisfies BCNF**.

2. **`daily_price_history` $(\underline{\text{Ticker}, \text{Trading\_Date}}, \dots)$:**
   - Sole non-trivial determinant is $\{\text{Ticker}, \text{Trading\_Date}\}$, which is the primary key.
   - Every determinant is a superkey $\implies$ **Strictly satisfies BCNF**.

3. **`corporate_action` $(\underline{\text{Action\_ID}}, \text{Ticker}, \text{Action\_Date}, \text{Action\_Type}, \text{Action\_Value})$:**
   - Determinant 1: $\text{Action\_ID}$ (enforced PK).
   - Determinant 2: $\{\text{Ticker}, \text{Action\_Date}, \text{Action\_Type}\}$ (enforced UNIQUE constraint `uq_corp_action`).
   - Both determinants are candidate keys $\implies$ **Strictly satisfies BCNF**.

4. **`current_fundamentals` $(\underline{\text{Ticker}}, \dots)$:**
   - Sole determinant is $\text{Ticker}$ (enforced PK).
   - Determinant is a superkey $\implies$ **Strictly satisfies BCNF**.

5. **`company` $(\underline{\text{Ticker}}, \text{Company\_Name}, \text{Sector\_ID})$:**
   - Primary key determinant: $\text{Ticker} \to \{\text{Company\_Name}, \text{Sector\_ID}\}$. $\text{Ticker}$ is a superkey.
   - *Inferred Candidate Key Nuance:* In the raw data, every `company_name` is distinct across all 49 companies ($\text{Company\_Name} \to \text{Ticker}$). However, in the database DDL, `company_name` has no UNIQUE constraint.
   - If $\text{Company\_Name}$ is recognized as a candidate key, both determinants are superkeys ($\implies$ BCNF). If not enforced, $\text{Ticker}$ is the sole determinant ($\implies$ BCNF). Under either interpretation, `company` **satisfies BCNF**.

6. **`stock_summary` (Reconciliation of Normal Form):**
   - **Strongest Supported Normal Form:** **BCNF (and 3NF)** under the enforced dependency set $F_{\text{enforced}} = \{\text{ticker} \to \text{all other attributes}\}$.
   - **Reasoning:** `ticker` is the sole candidate key. Every non-trivial functional dependency in $F_{\text{enforced}}$ has `ticker` as its determinant, which is a superkey.
   - **Analytical Assumptions:** This classification assumes that the algebraic formula defining $\text{total\_return\_pct}$ from $\text{starting\_price}$ and $\text{ending\_price}$ is an un-enforced computation rather than an active schema-level functional dependency constraint, and that snapshot valuation duplicates from `current_fundamentals` represent materialization rather than transitive functional violations. It functions as an intentional analytical cache.

7. **`portfolio_risk_sector_allocation` $(\underline{\text{Analysis\_ID}, \text{Sector\_ID}}, \text{Concentration\_Pct})$:**
   - Sole determinant is composite primary key $\{\text{Analysis\_ID}, \text{Sector\_ID}\}$.
   - Superkey determinant $\implies$ **Strictly satisfies BCNF**.

8. **`portfolio_holding` (Post-Migration 05):**
   - Candidate keys: $\text{Holding\_ID}$ (PK) and $\{\text{Portfolio\_ID}, \text{Ticker}\}$ (UNIQUE).
   - Both determinants are superkeys $\implies$ **Strictly satisfies BCNF**.

---

## 9. Lossless-Join Decomposition Proofs

### 9.1 Formal Lossless-Join Theorem (Heath's Theorem)
Let relation $R(U)$ with functional dependency set $F$ be decomposed into relations $R_1(U_1)$ and $R_2(U_2)$ such that $U = U_1 \cup U_2$.
The decomposition is **lossless** (i.e., $R = R_1 \bowtie R_2$) if and only if:
$$(U_1 \cap U_2) \to (U_1 \setminus U_2) \in F^+ \quad\text{OR}\quad (U_1 \cap U_2) \to (U_2 \setminus U_1) \in F^+$$
Equivalently: **The common attributes $(U_1 \cap U_2)$ must form a superkey of at least one of the decomposed relations.**

### 9.2 Exact Step-by-Step Proof for Binary Decompositions

#### Decomposition 1: Separating `daily_price_history` and `company_fundamentals`
- Original Relation: $R_{\text{market\_data}}$ (Attributes of price history and company metadata).
- Binary Decomposition Components:
  - $U_1$ (`daily_price_history`): $\{\text{Ticker}, \text{Trading\_Date}, \text{Open}, \text{High}, \text{Low}, \text{Close}, \text{Volume}, \text{Daily\_Return}, \text{Vol\_20D}, \text{MA\_50}, \text{MA\_200}\}$
  - $U_2$ (`company_fundamentals`): $\{\text{Ticker}, \text{Company\_Name}, \text{Sector}, \text{Market\_Cap}, \text{PE\_Ratio}, \text{Forward\_PE}, \text{Price\_to\_Book}, \text{Dividend\_Yield}, \text{EPS}, \text{Beta}, \text{PEG\_Ratio}\}$
- Common Attributes: $U_1 \cap U_2 = \{\text{Ticker}\}$
- Target Difference: $U_2 \setminus U_1 = \{\text{Company\_Name}, \text{Sector}, \text{Market\_Cap}, \dots\}$
- Functional Dependency: $\text{Ticker} \to (U_2 \setminus U_1) \in F^+$ ($FD_3, FD_4$).
- **Proof:** Because $(U_1 \cap U_2) \to (U_2 \setminus U_1)$, $\text{Ticker}$ is a superkey of `company_fundamentals`. By Heath's Theorem, the decomposition is **strictly lossless**.

#### Decomposition 2: Separating `company_raw` from `current_fundamentals`
- Original Relation: `company_fundamentals`
- Binary Decomposition Components:
  - $U_1$ (`company_raw`): $\{\text{Ticker}, \text{Company\_Name}, \text{Sector}\}$
  - $U_2$ (`current_fundamentals`): $\{\text{Ticker}, \text{PE\_Ratio}, \text{Forward\_PE}, \text{Price\_to\_Book}, \text{Dividend\_Yield}, \text{EPS}, \text{Beta}, \text{Fiscal\_Year}, \text{Market\_Cap}, \text{PEG\_Ratio}, \text{Last\_Updated}\}$
- Common Attributes: $U_1 \cap U_2 = \{\text{Ticker}\}$
- Functional Dependency: $\text{Ticker} \to U_2 \in F^+$.
- **Proof:** $\text{Ticker}$ is the candidate key of `current_fundamentals`. By Heath's Theorem, the decomposition is **strictly lossless**.

#### Decomposition 3: Separating `company` from `sector`
- Original Relation: `company_raw`
- Binary Decomposition Components:
  - $U_{\text{company}}$: $\{\text{Ticker}, \text{Company\_Name}, \text{Sector\_ID}\}$
  - $U_{\text{sector}}$: $\{\text{Sector\_ID}, \text{Sector\_Name}\}$
- Common Attributes: $U_{\text{company}} \cap U_{\text{sector}} = \{\text{Sector\_ID}\}$
- Target Difference: $U_{\text{sector}} \setminus U_{\text{company}} = \{\text{Sector\_Name}\}$
- Functional Dependency: $\text{Sector\_ID} \to \text{Sector\_Name} \in F^+$.
- **Proof:** Because $\text{Sector\_ID}$ is the candidate key of `sector`, $(U_{\text{company}} \cap U_{\text{sector}})$ forms a superkey of `sector`. By Heath's Theorem, the decomposition is **strictly lossless**.

### 9.3 Corporate Actions: Event Extraction vs Lossless Natural Join
An important academic correction must be documented regarding `corporate_action`:
- **Claim Corrected:** The creation of `corporate_action` is **NOT** a standard vertical lossless-join decomposition under Heath's Theorem.
- **Reasoning:**
  1. In the raw CSV relation $R_{\text{raw}}$, `Dividend` and `Stock_Split` were attributes recorded across all 287,310 dates. In $99.4\%$ of rows ($285,657$ rows), their values were $0.0$ or empty.
  2. Table `corporate_action` in PostgreSQL contains only **1,653 rows** because the ingestion pipeline (`scripts/ingest_data.py`) applied a **horizontal selection** ($\sigma_{\text{Dividend} > 0 \lor \text{Stock\_Split} > 0}$) and unpivoted the two columns into `action_type` and `action_value`.
  3. If a natural inner join is performed:
     $$\text{daily\_price\_history} \bowtie \text{corporate\_action}$$
     on `(ticker, trading_date = action_date)`, the resulting relation contains **only 1,653 rows**. All 285,657 trading dates without corporate actions are lost.
  4. **Reconstruction Condition:** Reconstructing the original flat historical CSV requires a **LEFT OUTER JOIN** combined with conditional projection and domain defaulting:
     ```sql
     SELECT 
         p.ticker, p.trading_date, p.open_price, p.high_price, p.low_price, p.close_price, p.volume,
         COALESCE(MAX(CASE WHEN c.action_type = 'Dividend' THEN c.action_value END), 0.0) AS dividend,
         COALESCE(MAX(CASE WHEN c.action_type = 'Stock_Split' THEN c.action_value END), 0.0) AS stock_split
     FROM daily_price_history p
     LEFT JOIN corporate_action c ON p.ticker = c.ticker AND p.trading_date = c.action_date
     GROUP BY p.ticker, p.trading_date, p.open_price, p.high_price, p.low_price, p.close_price, p.volume;
     ```
  5. **Academic Conclusion:** `corporate_action` represents a **lossless discrete-event extraction with sparse-null horizontal selection**, whose exact reconstruction depends on outer join semantics and domain defaulting rather than Heath's natural join theorem.

---

## 10. Dependency-Preservation Discussion

### 10.1 Formal Definition of Dependency Preservation
A decomposition $D = \{R_1, R_2, \dots, R_k\}$ of relation $R$ with functional dependencies $F$ is **dependency-preserving** if:
$$\Big( \bigcup_{i=1}^k \pi_{R_i}(F) \Big)^+ = F^+$$
where $\pi_{R_i}(F)$ denotes the projection of $F$ onto attribute set $R_i$. That is, every functional dependency in $F$ must be verifiable by inspecting individual relations without computing joins.

### 10.2 Enforced vs Inferred Dependencies

| Functional Dependency | Target Relation(s) | Preservation Mechanism | Enforcement Classification |
| :--- | :--- | :--- | :--- |
| $\{\text{Ticker}, \text{Trading\_Date}\} \to \text{OHLCV, Indicators}$ | `daily_price_history` | Composite Primary Key | **Enforced in DDL** |
| $\text{Ticker} \to \{\text{Company\_Name}, \text{Sector\_ID}\}$ | `company` | Primary Key on `ticker` | **Enforced in DDL** |
| $\text{Sector\_ID} \to \text{Sector\_Name}$ | `sector` | Primary Key on `sector_id` | **Enforced in DDL** |
| $\text{Sector\_Name} \to \text{Sector\_ID}$ | `sector` | Unique Constraint on `sector_name` | **Enforced in DDL** |
| $\text{Ticker} \to \text{Fundamentals}$ | `current_fundamentals` | Primary Key on `ticker` | **Enforced in DDL** |
| $\{\text{Ticker}, \text{Action\_Date}, \text{Action\_Type}\} \to \text{Action\_Value}$ | `corporate_action` | Unique Constraint `uq_corp_action` | **Enforced in DDL** |
| $\text{Ticker} \to \text{Summary Metrics}$ | `stock_summary` | Primary Key on `ticker` | **Enforced in DDL** |
| $\text{Ticker} \to \text{Sector\_Name}$ | `company` $\bowtie$ `sector` | Transitive join path via FK `sector_id` | **Enforced across join** |
| $\text{Company\_Name} \to \text{Ticker}$ | `company` | 49 unique names observed in data | **Inferred from Data** (No UNIQUE constraint) |
| $\{\text{Starting\_Price}, \text{Ending\_Price}\} \to \text{Total\_Return\_%}$ | `stock_summary` | Arithmetic calculation formula | **Inferred in Logic** (No DDL constraint) |

**Academic Conclusion:**
All primary functional dependencies defining the entity attributes are **strictly preserved and enforced** in the decomposed schema through primary keys, unique constraints, and foreign key references. Secondary dependencies (such as company name uniqueness) are observed in the data domain but are not enforced by explicit database constraints.

---

## 11. Complete Before-and-After Column Mapping

### 11.1 Primary Historical Dataset (`nifty50_historical_data.csv` — 25 Columns)

| # | Original Column | Meaning | Original Source | Final Relation | Final Column | Operation / Reason for Placement |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `Date` | Calendar date of trade | Historical CSV | `daily_price_history` | `trading_date` | Preserved; composite PK component `(ticker, trading_date)`; truncated ISO timestamp string to `DATE`. |
| 2 | `Ticker` | Natural stock symbol | Historical CSV | `company` | `ticker` | Preserved; natural Primary Key of `company`; foreign key across all child tables. |
| 3 | `Company_Name` | Registered corporate name | Historical CSV | `company` | `company_name` | Decomposed into 2NF `company` to eliminate 287k partial repetitions. |
| 4 | `Sector` | Macroeconomic sector | Historical CSV | `sector` | `sector_name` | Decomposed into 3NF `sector` via surrogate `sector_id` to eliminate transitive FD. |
| 5 | `Open` | Session opening price | Historical CSV | `daily_price_history` | `open_price` | Preserved; mapped to NUMERIC(14,4). |
| 6 | `High` | Session peak price | Historical CSV | `daily_price_history` | `high_price` | Preserved; mapped to NUMERIC(14,4). |
| 7 | `Low` | Session trough price | Historical CSV | `daily_price_history` | `low_price` | Preserved; mapped to NUMERIC(14,4). |
| 8 | `Close` | Session closing price | Historical CSV | `daily_price_history` | `close_price` | Preserved; mapped to NUMERIC(14,4). |
| 9 | `Volume` | Traded share volume | Historical CSV | `daily_price_history` | `volume` | Preserved; mapped to BIGINT with CHECK (volume >= 0). |
| 10 | `Dividend` | Per-share cash dividend | Historical CSV | `corporate_action` | `action_value` | Filtered where $>0$ (1,555 rows); extracted to 2NF discrete event ledger (`action_type='Dividend'`). |
| 11 | `Stock_Split` | Share split ratio | Historical CSV | `corporate_action` | `action_value` | Filtered where $>0$ (98 rows); extracted to 2NF discrete event ledger (`action_type='Stock_Split'`). |
| 12 | `Daily_Return` | Day-over-day return | Historical CSV | `daily_price_history` | `daily_return` | Preserved; precomputed return decimal. |
| 13 | `Volatility_20D`| 20-day return volatility | Historical CSV | `daily_price_history` | `vol_20d` | Preserved; technical rolling volatility indicator. |
| 14 | `MA_50` | 50-day moving average | Historical CSV | `daily_price_history` | `ma_50` | Preserved; technical trend indicator. |
| 15 | `MA_200` | 200-day moving average | Historical CSV | `daily_price_history` | `ma_200` | Preserved; technical long-term trend indicator. |
| 16 | `Market_Cap` | Market capitalization | Historical CSV | `current_fundamentals` | `market_cap` | Decomposed to 2NF `current_fundamentals`; static valuation snapshot. |
| 17 | `PE_Ratio` | Trailing P/E ratio | Historical CSV | `current_fundamentals` | `pe_ratio` | Decomposed to 2NF `current_fundamentals`; static valuation ratio. |
| 18 | `Forward_PE` | Forward P/E ratio | Historical CSV | `current_fundamentals` | `forward_pe` | Decomposed to 2NF `current_fundamentals`; static valuation ratio. |
| 19 | `PEG_Ratio` | P/E to growth ratio | Historical CSV | `current_fundamentals` | `peg_ratio` | Preserved as nullable column; empirically 100% NULL across all 287,310 rows. |
| 20 | `Price_to_Book` | Price-to-book multiple | Historical CSV | `current_fundamentals` | `price_to_book` | Decomposed to 2NF `current_fundamentals`; static book multiple. |
| 21 | `Dividend_Yield`| Annual dividend yield | Historical CSV | `current_fundamentals` | `dividend_yield` | Decomposed to 2NF `current_fundamentals`; static yield decimal. |
| 22 | `EPS` | Earnings per share | Historical CSV | `current_fundamentals` | `eps` | Decomposed to 2NF `current_fundamentals`; static corporate earnings metric. |
| 23 | `Beta` | Market risk coefficient | Historical CSV | `current_fundamentals` | `beta` | Decomposed to 2NF `current_fundamentals`; systematic risk factor. |
| 24 | `52Week_High` | Rolling 52-week peak | Historical CSV | *Omitted (Derivable)* | — | Omitted from base tables during ETL ingestion; dynamically computable from `daily_price_history` via `MAX(high_price)` over trailing 252 sessions. |
| 25 | `52Week_Low` | Rolling 52-week trough | Historical CSV | *Omitted (Derivable)* | — | Omitted from base tables during ETL ingestion; dynamically computable from `daily_price_history` via `MIN(low_price)` over trailing 252 sessions. |

### 11.2 Secondary Dataset (`nifty50_summary_statistics.csv` — 18 Columns)

| # | Original Column | Meaning | Original Source | Final Relation | Final Column | Operation / Reason for Placement |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `Ticker` | Stock symbol | Summary CSV | `stock_summary` | `ticker` | Preserved; primary key referencing `company(ticker)`. |
| 2 | `Company_Name` | Company name | Summary CSV | *Omitted from table*| — | Redundant with `company.company_name`; resolved via join. |
| 3 | `Sector` | Sector name | Summary CSV | *Omitted from table*| — | Redundant with `sector.sector_name`; resolved via join. |
| 4 | `First_Date` | First trade date | Summary CSV | `stock_summary` | `first_trading_date` | Preserved; aggregate metric. |
| 5 | `Last_Date` | Last trade date | Summary CSV | `stock_summary` | `last_trading_date` | Preserved; aggregate metric. |
| 6 | `Total_Trading_Days`| Lifetime trade days | Summary CSV | `stock_summary` | `total_trading_days` | Preserved; aggregate metric with CHECK (total_trading_days > 0). |
| 7 | `Starting_Price`| First trade close | Summary CSV | `stock_summary` | `starting_price` | Preserved; aggregate metric. |
| 8 | `Ending_Price` | Last trade close | Summary CSV | `stock_summary` | `ending_price` | Preserved; aggregate metric. |
| 9 | `Total_Return_%`| Cumulative return | Summary CSV | `stock_summary` | `total_return_pct` | Preserved; aggregate percentage metric. |
| 10 | `Highest_Price` | All-time high price | Summary CSV | `stock_summary` | `highest_price` | Preserved; aggregate metric. |
| 11 | `Lowest_Price` | All-time low price | Summary CSV | `stock_summary` | `lowest_price` | Preserved; aggregate metric. |
| 12 | `Avg_Daily_Volume`| Mean daily volume | Summary CSV | `stock_summary` | `avg_daily_volume` | Preserved; aggregate volume metric. |
| 13 | `Total_Dividends_Paid`| Lifetime dividends | Summary CSV | `stock_summary` | `total_dividends_paid`| Preserved; sum of lifetime dividends. |
| 14 | `Number_of_Splits`| Lifetime stock splits| Summary CSV | `stock_summary` | `number_of_splits` | Preserved; aggregate split count with CHECK (number_of_splits >= 0). |
| 15 | `Avg_Daily_Return_%`| Mean daily return | Summary CSV | `stock_summary` | `avg_daily_return_pct`| Preserved; mean return percentage. |
| 16 | `Volatility_%` | Lifetime volatility | Summary CSV | `stock_summary` | `volatility_pct` | Preserved; annualized volatility percentage. |
| 17 | `Current_Market_Cap`| Market cap cache | Summary CSV | `stock_summary` | `current_market_cap`| Preserved; analytical precomputed cache. |
| 18 | `Current_PE_Ratio`| P/E ratio cache | Summary CSV | `stock_summary` | `current_pe_ratio` | Preserved; analytical precomputed cache. |

---

## 12. Anomaly Analysis & Physical Storage Audit

### 12.1 Update Anomalies

#### Unnormalized Relation Defect:
In the flat relation $R_{\text{raw}}$, company names, sector classifications, and fundamental metrics are repeated across every daily trading session.
- **Observed Source Metrics:**
  - `AXISBANK.NS` appears on **exactly 6,767 distinct trading dates**.
  - `INFY.NS` appears on **exactly 6,767 distinct trading dates**.
  - `Financials` sector appears on **exactly 53,903 rows**.
- If Axis Bank updates its registered corporate entity name:
  - In the unnormalized CSV, an update query must search and modify **all 6,767 records**.
  - If a network error or system crash interrupts the transaction after updating 3,000 rows, the database becomes corrupt and inconsistent: queries filtering on the old name return 3,767 rows, while queries filtering on the new name return 3,000 rows.

#### Normalized Solution:
In the 3NF schema:
```sql
UPDATE company SET company_name = 'Axis Bank Ltd.' WHERE ticker = 'AXISBANK.NS';
```
- Modifies **exactly 1 row**.
- Relational integrity is mathematically guaranteed.

---

### 12.2 Insertion Anomalies

#### Unnormalized Relation Defect:
In $R_{\text{raw}}$, the candidate key is composite: $\{\text{Ticker}, \text{Date}\}$.
- By the **Entity Integrity Rule** of the relational model, no attribute participating in a candidate key may contain NULL.
- If a newly listed company (e.g., `JIOFIN.NS`) is registered before its initial public trading session:
  - It cannot be inserted into $R_{\text{raw}}$ because `Date`, `Open`, `High`, `Low`, `Close`, and `Volume` do not yet exist.
  - Inserting artificial dummy dates (e.g., `1900-01-01`) or NULLs corrupts time-series aggregation queries.
- Similarly, a new economic sector (e.g., *Renewable Energy*) cannot be added to the system until a listed company in that sector has recorded trading sessions.

#### Normalized Solution:
Independent entities possess independent base tables:
```sql
INSERT INTO sector (sector_name) VALUES ('Renewable Energy');
INSERT INTO company (ticker, company_name, sector_id) VALUES ('NEWCO.NS', 'New Company Ltd.', 14);
```
- Companies and sectors are registered immediately with zero dependency on trading session availability.

---

### 12.3 Deletion Anomalies

#### Unnormalized Relation Defect:
If an administrator purges historical price sessions prior to 2005 to reclaim disk storage, and an acquired or unlisted stock only traded during that window:
- Deleting the historical price rows **unintentionally purges the corporate identity, sector classification, and fundamental valuation history**.
- Corporate history is permanently lost because it has no independent existence outside the trading session tuples.

#### Normalized Solution:
Child rows in `daily_price_history` can be purged safely:
```sql
DELETE FROM daily_price_history WHERE ticker = 'AXISBANK.NS' AND trading_date < '2005-01-01';
```
- Deletes historical session rows while `company`, `sector`, and `current_fundamentals` remain 100% intact.

---

### 12.4 Physical Storage Audit & Measurement Methodology

#### Academic Evaluation of Storage Metrics:
To avoid methodologically invalid comparisons (such as comparing uncompressed plain-text files directly to compressed binary database archives), the project reports physical storage measurements as distinct metrics:

| Storage Layer | Physical Entity | Measured Size | Description / Measurement Methodology |
| :--- | :--- | :---: | :--- |
| **Raw Source Files** | `nifty50_historical_data.csv` | 87,715,220 bytes (~87.7 MB) | Plain-text uncompressed CSV on filesystem. |
| **Raw Source Files** | `nifty50_summary_statistics.csv` | 13,731 bytes (~13.7 KB) | Plain-text uncompressed CSV on filesystem. |
| **PostgreSQL Table Heap**| `daily_price_history` | 31,195,136 bytes (~30.0 MB) | Physical 8 KB table pages for 287,310 tuples. |
| **PostgreSQL Indexes** | `daily_price_history` | 19,677,184 bytes (~19.0 MB) | B-tree indexes (`daily_price_history_pkey`, `idx_price_date`, `idx_price_ticker`). |
| **PostgreSQL Table Heap**| `company` + `sector` + `current_fundamentals` + `corporate_action` | 139,264 bytes (~136 kB) | Combined normalized entity table heaps. |
| **PostgreSQL Total Database**| `stock_market_db` | 61,298,367 bytes (~58.0 MB) | Total on-disk relational cluster storage (heaps, indexes, system catalogs, WAL). |
| **Compressed Backup** | `stock_market_db_pre_migration_05...dump` | 10,488,713 bytes (~10.0 MB) | `pg_dump -Fc` custom-format compressed binary archive. |

#### Qualitative Normalization Assessment:
Normalization eliminates the repetition of company and sector text strings across all 287,310 rows of historical price data, isolating corporate identity attributes into `company` (49 rows) and `sector` (13 rows). Because the project did not maintain an unnormalized single-table PostgreSQL database populated with the raw 25-column dataset, no valid like-for-like physical database storage reduction can be measured. The observed physical sizes (plain-text CSV, PostgreSQL table heaps, B-tree indexes, and compressed dump archive) reflect distinct storage formats and physical page layouts rather than a direct empirical delta. Conceptually, normalizing string attributes avoids duplicated character storage in table pages and reduces tuple width in `daily_price_history`, benefiting sequential scans and cache efficiency.

---

## 13. Final Relational Schema & Database Constraints

The normalized relational database deployed in PostgreSQL (`stock_market_db`) comprises 15 base tables and 6 analytical views:

```sql
-- 1. Master Sector Taxonomy (BCNF)
CREATE TABLE sector (
    sector_id SERIAL PRIMARY KEY,
    sector_name TEXT NOT NULL UNIQUE
);

-- 2. Listed Company Registry (BCNF)
CREATE TABLE company (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector_id INT NOT NULL REFERENCES sector(sector_id) ON DELETE RESTRICT
);

-- 3. Daily Historical Price Ledger (BCNF)
CREATE TABLE daily_price_history (
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE CASCADE,
    trading_date DATE NOT NULL,
    open_price NUMERIC(14,4),
    high_price NUMERIC(14,4),
    low_price NUMERIC(14,4),
    close_price NUMERIC(14,4),
    volume BIGINT CHECK (volume >= 0),
    daily_return NUMERIC(10,4),
    vol_20d NUMERIC(10,4),
    ma_50 NUMERIC(14,4),
    ma_200 NUMERIC(14,4),
    PRIMARY KEY (ticker, trading_date)
);

-- 4. Discrete Corporate Actions Ledger (BCNF)
CREATE TABLE corporate_action (
    action_id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL REFERENCES company(ticker) ON DELETE CASCADE,
    action_date DATE NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('Dividend', 'Stock_Split')),
    action_value NUMERIC(14,4) NOT NULL CHECK (action_value > 0),
    CONSTRAINT uq_corp_action UNIQUE (ticker, action_date, action_type)
);

-- 5. Latest Fundamental Snapshot (BCNF)
CREATE TABLE current_fundamentals (
    ticker TEXT PRIMARY KEY REFERENCES company(ticker) ON DELETE CASCADE,
    pe_ratio NUMERIC(10,4),
    forward_pe NUMERIC(10,4),
    price_to_book NUMERIC(10,4),
    dividend_yield NUMERIC(10,4),
    eps NUMERIC(14,4),
    beta NUMERIC(10,4),
    fiscal_year INT,
    market_cap NUMERIC(22,2),
    peg_ratio NUMERIC(10,4),
    last_updated DATE NOT NULL DEFAULT CURRENT_DATE
);

-- 6. Analytical Summary Reporting Cache (Analytical Rollup)
CREATE TABLE stock_summary (
    ticker TEXT PRIMARY KEY REFERENCES company(ticker) ON DELETE CASCADE,
    first_trading_date DATE NOT NULL,
    last_trading_date DATE NOT NULL,
    total_trading_days INT NOT NULL CHECK (total_trading_days > 0),
    starting_price NUMERIC(16,4),
    ending_price NUMERIC(16,4),
    total_return_pct NUMERIC(18,4),
    highest_price NUMERIC(16,4),
    lowest_price NUMERIC(16,4),
    avg_daily_volume NUMERIC(18,2),
    total_dividends_paid NUMERIC(16,4),
    number_of_splits INT NOT NULL DEFAULT 0 CHECK (number_of_splits >= 0),
    avg_daily_return_pct NUMERIC(10,4),
    volatility_pct NUMERIC(10,4),
    current_market_cap NUMERIC(22,2),
    current_pe_ratio NUMERIC(10,4)
);
```

---

## PART B: POSTGRESQL APPLICATION SCHEMA NORMALIZATION

## 14. PostgreSQL Schema Normalization & Migration 05

Following the ingestion of raw market datasets, subsequent operational extensions in Migration 04 introduced anomalies in the application schema. Migration 05 was designed and deployed to resolve these defects.

### 14.1 The Pre-Migration 05 Violations
1. **Transitive Dependency in `portfolio_holding` (3NF Violation):**
   - In Migration 04, relation `user_portfolio` was introduced:
     $$\text{user\_portfolio}(\underline{\text{portfolio\_id}}, \text{user\_id}, \text{portfolio\_name}, \dots)$$
   - However, `portfolio_holding` stored both `user_id` and `portfolio_id`:
     $$\text{portfolio\_holding}(\underline{\text{holding\_id}}, \text{holding\_id} \to \text{portfolio\_id} \to \text{user\_id})$$
   - Because `portfolio_id` determined `user_id`, retaining `user_id` in `portfolio_holding` created a **transitive functional dependency violating 3NF**.
2. **Transaction History Loss on Holding Deletion:**
   - `portfolio_transaction` used a composite foreign key `(holding_id, user_id) REFERENCES portfolio_holding(holding_id, user_id)`.
   - When a user completely liquidated a holding, deleting the holding record was impossible without either deleting associated trade records (destroying financial audit trails) or leaving zero-share holding rows.
3. **Non-Atomic JSONB in `portfolio_risk_analysis` (1NF Violation):**
   - Column `sector_concentration` stored nested JSONB objects (e.g., `{"IT": 54.55, "Energy": 45.45}`), violating 1NF scalar atomicity and preventing relational SQL joins.

### 14.2 Transformations Executed by Migration 05
Executed via `sql/migration/05_pure_3nf_and_risk_normalization.sql`:

1. **Pure 3NF Refactoring for `portfolio_holding`:**
   - Enforced `portfolio_id NOT NULL`.
   - Added candidate key `uq_portfolio_holding_ticker UNIQUE (portfolio_id, ticker)`.
   - Dropped the redundant transitive column `user_id`:
     ```sql
     ALTER TABLE portfolio_holding DROP COLUMN user_id CASCADE;
     ```
   - Ownership is now resolved cleanly through relational join: $\text{holding} \bowtie \text{user\_portfolio} \bowtie \text{app\_user}$.

2. **Immutable Transaction History with `ON DELETE SET NULL`:**
   - Replaced composite foreign key with single-column foreign key:
     ```sql
     ALTER TABLE portfolio_transaction 
     ADD CONSTRAINT fk_transaction_holding 
     FOREIGN KEY (holding_id) REFERENCES portfolio_holding(holding_id) 
     ON DELETE SET NULL;
     ```
   - When a holding position is liquidated or deleted, `transaction.holding_id` becomes `NULL`, while `transaction_id`, `portfolio_id`, `user_id`, `ticker`, `price`, `quantity`, and `date` remain permanently preserved in the immutable ledger.
   - Cross-user holding isolation is enforced by trigger `trg_portfolio_transaction_consistency` executing `fn_enforce_portfolio_transaction_consistency()`.

3. **Pure 1NF Child Relation for Risk Sector Allocations:**
   - Created normalized relation:
     ```sql
     CREATE TABLE portfolio_risk_sector_allocation (
         analysis_id       INTEGER NOT NULL REFERENCES portfolio_risk_analysis(analysis_id) ON DELETE CASCADE,
         sector_id         INTEGER NOT NULL REFERENCES sector(sector_id) ON DELETE RESTRICT,
         concentration_pct NUMERIC(5,2) NOT NULL CHECK (concentration_pct >= 0 AND concentration_pct <= 100),
         PRIMARY KEY (analysis_id, sector_id)
     );
     ```
   - Migrated all JSONB allocations into scalar tuples with 100% mathematical precision.
   - Retained column `portfolio_risk_analysis.sector_concentration` during Phase 1 for backward compatibility.

4. **Dynamic Backward Compatibility View:**
   - Created view `v_portfolio_risk_analysis` to dynamically synthesize legacy JSONB on read:
     ```sql
     CREATE VIEW v_portfolio_risk_analysis AS
     SELECT 
         pra.analysis_id, pra.user_id, pra.analysis_date,
         pra.sharpe_ratio, pra.volatility, pra.max_drawdown,
         COALESCE(
             (SELECT jsonb_object_agg(s.sector_name, prsa.concentration_pct)
              FROM portfolio_risk_sector_allocation prsa
              JOIN sector s ON prsa.sector_id = s.sector_id
              WHERE prsa.analysis_id = pra.analysis_id),
             pra.sector_concentration,
             '{}'::jsonb
         ) AS sector_concentration,
         pra.transaction_context
     FROM portfolio_risk_analysis pra;
     ```

5. **Stored Procedure Signatures:**
   - Replaced legacy 5-parameter versions of `record_stock_purchase` and `record_stock_sale` with clean 6-parameter versions accepting `p_portfolio_id`, explicitly purging obsolete overloads.

---

## 15. Validation Results & Data Integrity

### 15.1 Production Baseline vs Post-Migration Verification

Every table was queried in the live production database before and after Migration 05 to verify zero data loss:

| Table Name | Pre-Migration Baseline | Post-Migration Actual | Parity Status | Verification Notes |
| :--- | :---: | :---: | :---: | :--- |
| `app_user` | 137 | 137 | **100% Intact** | Zero user account modifications. |
| `user_portfolio` | 149 | 149 | **100% Intact** | All virtual cash balances preserved. |
| `portfolio_holding` | 36 | 36 | **100% Intact** | Refactored to Pure 3NF; zero row delta. |
| `portfolio_transaction` | 66 | 66 | **100% Intact** | All trade execution records preserved. |
| `portfolio_transaction_audit` | 66 | 66 | **100% Intact** | Audit ledger completely intact. |
| `portfolio_risk_analysis` | 2 | 2 | **100% Intact** | Parent risk records preserved. |
| `portfolio_risk_sector_allocation` | 0 | 4 | **+4 Normalized** | Migrated from JSONB: Analysis 1 (IT: 54.55%, Energy: 45.45%), Analysis 2 (IT: 54.55%, Energy: 45.45%). |
| `daily_price_history` | 287,310 | 287,310 | **100% Intact** | All 287k price rows preserved. |
| `corporate_action` | 1,653 | 1,653 | **100% Intact** | All dividends and splits preserved. |
| `company` | 49 | 49 | **100% Intact** | All listed equities preserved. |
| `sector` | 13 | 13 | **100% Intact** | All 13 master sectors preserved. |
| `current_fundamentals` | 49 | 49 | **100% Intact** | All 49 valuation snapshots preserved. |
| `stock_summary` | 49 | 49 | **100% Intact** | Summary statistics cache preserved. |
| `user_watchlist` | 2 | 2 | **100% Intact** | User watchlists preserved. |

### 15.2 Production Backup and Restore Evidence
- **Backup File:** `data/backups/stock_market_db_pre_migration_05_20261027_095415.dump`
- **File Size:** 10,488,713 bytes (~10.0 MB)
- **SHA-256 Checksum:** `5307e2941ee12a51380554d1b89f3c33e38aa209251d1d2fb29b7f458f3edea0`
- **Verification:** Empirically restored into disposable database `dbs_migration05_restore_validation_20261027_095415`. Confirmed 100% row count, schema, and constraint equivalence before committing live migration.

### 15.3 Automated Regression Testing
1. **Portfolio Lifecycle SQL Test Suite (`tests/test_portfolio_lifecycle.sql`):**
   - Executed 6 automated test phases in an isolated rolled-back transaction: Buy position, Partial sell, Full liquidation, Position re-entry, `ON DELETE SET NULL` preservation, Rollback isolation.
   - Result: **6 passed, 0 failed**.
2. **Trigger Consistency SQL Test Suite (`tests/test_triggers.sql`):**
   - Validated cash balance checks, cross-user holding isolation, transaction audit logging, and immutability.
   - Result: **8 passed, 0 failed**.
3. **Pytest Regression Suite (`pytest tests/ -v`):**
   - Executed against the live migrated schema.
   - Result: **70 passed in 8.28s (100% pass rate)**.
4. **Live API Smoke Tests:**
   - FastAPI server (`http://127.0.0.1:8000`):
   - `GET /api/health` $\to$ `200 OK`
   - `GET /api/dashboard` $\to$ `200 OK`
   - `GET /api/prices/latest` $\to$ `200 OK` (49 prices)
   - `GET /api/companies` $\to$ `200 OK` (49 companies)
   - `GET /api/sectors` $\to$ `200 OK` (13 sectors)

---

## 16. Limitations, Assumptions, and Deferred Migration 06

### 16.1 Analytical Design Limitations
1. **Point-in-Time Fundamental Snapshots:**
   - In `nifty50_historical_data.csv`, fundamental valuation metrics (`PE_Ratio`, `Market_Cap`, `EPS`, etc.) were static snapshot values as of January 30, 2026, duplicated identically across all 287,310 dates. Real-world corporate fundamentals fluctuate quarterly. The schema isolates fundamentals into `current_fundamentals` to capture the latest snapshot. If historical quarterly financial statements are acquired in the future, a relation `historical_fundamentals(ticker, fiscal_quarter, fiscal_year, ...)` can be added without altering `daily_price_history`.
2. **`PEG_Ratio` Data Quality:**
   - In the raw dataset, `PEG_Ratio` was **100% NULL** across all 287,310 records. It is retained as a nullable column in `current_fundamentals` for future data pipelines.
3. **Intentional Denormalization in `stock_summary`:**
   - `stock_summary` contains derived attributes (`total_return_pct`) and duplicate metrics from `current_fundamentals`. This is an intentional reporting cache trade-off to support sub-millisecond dashboard exploration without scanning 287k rows on every request.
4. **TimescaleDB Operational Isolation:**
   - TimescaleDB (`stock_timescale_db` on port 5434) hosts an independent partitioned copy of `daily_price_history` for analytical charting. It shares no foreign keys with PostgreSQL and is strictly governed by application ETL.

### 16.2 Rationale for Deferring Migration 06
Migration 06 (`sql/migration/06_retire_risk_jsonb_column.sql`) physically drops column `portfolio_risk_analysis.sector_concentration`.

It is deliberately held in a **deferred state** for a 24–48 hour observation window based on the following engineering principles:
1. **Zero-Downtime Consumer Transition:** External reporting tools, third-party consumers, and cached dashboard queries reading raw JSONB from `portfolio_risk_analysis` must complete their transition to view `v_portfolio_risk_analysis` or table `portfolio_risk_sector_allocation`.
2. **Instant Rollback Safety:** While column `portfolio_risk_analysis.sector_concentration` remains in place, executing [`05_pure_3nf_and_risk_normalization_rollback.sql`](file:///Users/easwarap/.gemini/antigravity-ide/scratch/DBS-Stock-Market-Analytics-friend/sql/migration/05_pure_3nf_and_risk_normalization_rollback.sql) can restore the pre-migration schema instantaneously without restoring a physical database dump.
3. **Execution Condition:** Migration 06 will be reviewed and applied once production query logs confirm zero residual reads on the legacy physical JSONB column.
