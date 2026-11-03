"""
sec07_keys_normalization.py - Keys, Constraints, Functional Dependencies, and Normalization Proofs
"""

from docx import Document
from docx.shared import Inches
from report_utils import (
    add_h1, add_h2, add_h3, add_body_p, add_bullet_p, add_callout_box, create_styled_table
)

def build_keys_and_normalization(doc: Document):
    """Renders Section 8: Keys, Constraints, Functional Dependencies, and Normalization."""
    add_h1(doc, "8. Keys, Constraints, Functional Dependencies, and Normalization")
    
    add_body_p(
        doc,
        "Database normalization is the mathematical cornerstone of relational theory (Codd, 1970). It ensures that database schemas remain free from data redundancy and modification anomalies while preserving functional dependencies and lossless-join guarantees. This section presents formal mathematical derivations of candidate keys, functional dependency sets, lossless decompositions via Heath's Theorem, and normalization proofs spanning 1NF through BCNF."
    )
    
    add_h2(doc, "8.1 Raw Dataset Architecture and Candidate Key Proof")
    add_body_p(
        doc,
        "The foundation dataset originates from multi-asset historical price records (all_stocks_5yr.csv) combined with company profiles. Consider the unnormalized universal relation:"
    )
    add_body_p(
        doc,
        "R_UNF = {Ticker, CompanyName, SectorName, Date, Open, High, Low, Close, Volume, Dividend, SplitRatio}",
        italic_prefix="Universal Relation Schema: "
    )
    add_body_p(
        doc,
        "To find all minimal candidate keys, we determine the attribute closure under the real-world semantic functional dependencies governing financial markets:"
    )
    add_bullet_p(doc, "Ticker -> CompanyName, SectorName", bold_prefix="FD1: ")
    add_bullet_p(doc, "{Ticker, Date} -> Open, High, Low, Close, Volume", bold_prefix="FD2: ")
    add_bullet_p(doc, "{Ticker, Date} -> Dividend, SplitRatio (when corporate actions occur)", bold_prefix="FD3: ")
    add_bullet_p(doc, "SectorName -> SectorDescription (if present)", bold_prefix="FD4: ")
    
    add_body_p(
        doc,
        "Proof of Candidate Key: Let X = {Ticker, Date}. Computing attribute closure X+:\n"
        "1. X+ contains {Ticker, Date} (trivial).\n"
        "2. Applying FD1: {Ticker} in X+ => CompanyName, SectorName in X+.\n"
        "3. Applying FD2: {Ticker, Date} in X+ => Open, High, Low, Close, Volume in X+.\n"
        "4. Applying FD3: {Ticker, Date} in X+ => Dividend, SplitRatio in X+.\n"
        "Therefore, X+ = {Ticker, CompanyName, SectorName, Date, Open, High, Low, Close, Volume, Dividend, SplitRatio} = R_UNF.\n"
        "Since neither {Ticker}+ nor {Date}+ can determine the remaining attributes, {Ticker, Date} is irreducible and strictly minimal. Hence, {Ticker, Date} is the sole minimal candidate key for market quotations."
    )
    
    add_h2(doc, "8.2 Table-by-Table Candidate Keys and Functional Dependencies")
    add_body_p(
        doc,
        "The following matrix summarizes the minimal candidate keys and complete functional dependency sets across the normalized relational schema:"
    )
    
    headers = ["Relational Table", "Minimal Candidate Key(s)", "Verified Functional Dependencies (FD Set)", "Normal Form Achieved"]
    norm_table = [
        ["sector", "{sector_id}, {sector_name}", "sector_id -> sector_name; sector_name -> sector_id", "BCNF"],
        ["company", "{ticker}", "ticker -> name, sector_id, exchange, ipo_year, is_active", "BCNF"],
        ["daily_price_history", "{ticker, date}", "{ticker, date} -> open, high, low, close, volume", "BCNF"],
        ["corporate_action", "{action_id}, {ticker, action_date, action_type}", "action_id -> ticker, action_date, action_type, value", "BCNF"],
        ["stock_summary", "{ticker}", "ticker -> current_price, change_percent, 52w_high, 52w_low", "BCNF (Analytical Cache)"],
        ["app_user", "{user_id}, {email}, {username}", "user_id -> email, username, password_hash, role, created_at", "BCNF"],
        ["user_portfolio", "{portfolio_id}, {user_id, portfolio_name}", "portfolio_id -> user_id, portfolio_name, cash_balance", "BCNF"],
        ["portfolio_holding", "{portfolio_id, ticker}", "{portfolio_id, ticker} -> quantity, avg_buy_price", "BCNF (Pure 3NF)"],
        ["portfolio_transaction", "{transaction_id}", "transaction_id -> portfolio_id, ticker, type, quantity, price", "BCNF"],
        ["transaction_audit_log", "{audit_id}", "audit_id -> table_name, operation, record_id, changed_by, timestamp", "BCNF (Immutable Log)"],
        ["portfolio_risk_analysis", "{analysis_id}, {portfolio_id, calculated_at}", "analysis_id -> portfolio_id, sharpe_ratio, max_drawdown", "BCNF"],
        ["portfolio_risk_sector_allocation", "{allocation_id}, {analysis_id, sector_name}", "allocation_id -> analysis_id, sector_name, allocation_pct", "BCNF (1NF Decomposed)"]
    ]
    create_styled_table(
        doc,
        headers,
        norm_table,
        [Inches(1.8), Inches(1.5), Inches(2.2), Inches(1.0)]
    )
    
    add_h2(doc, "8.3 Detailed Normalization Journey (1NF through BCNF)")
    
    add_h3(doc, "8.3.1 First Normal Form (1NF)")
    add_body_p(
        doc,
        "A relation is in 1NF if and only if all domain values are atomic and there are no repeating groups. In early iterations, two 1NF violations existed:\n"
        "1. In raw financial files, corporate actions (dividends and splits) were embedded as comma-delimited strings or sparse repeating columns.\n"
        "2. In early risk models, portfolio sector exposure was stored as a single semi-structured JSONB blob inside portfolio_risk_analysis (e.g., {'Technology': 45.2, 'Healthcare': 20.1}).\n"
        "Resolution: In Migration 05, the JSONB blob was fully decomposed into the atomic table portfolio_risk_sector_allocation, where each tuple stores exactly one (analysis_id, sector_name, allocation_percentage) triple with atomic numerical domain."
    )
    
    add_h3(doc, "8.3.2 Second Normal Form (2NF)")
    add_body_p(
        doc,
        "A relation is in 2NF if it is in 1NF and no non-prime attribute is partially dependent on any candidate key. In R_UNF, the candidate key is composite: {Ticker, Date}.\n"
        "However, CompanyName and SectorName depend solely on {Ticker}, which is a proper subset of the composite key (Ticker -> CompanyName). This represents a severe partial dependency.\n"
        "Resolution: Decompose R_UNF into:\n"
        "• COMPANY(ticker, name, sector_id)\n"
        "• DAILY_PRICE_HISTORY(ticker, date, open, high, low, close, volume)\n"
        "In DAILY_PRICE_HISTORY, every non-prime attribute (open, high, low, close, volume) depends on the full composite key {ticker, date}, satisfying 2NF."
    )
    
    add_h3(doc, "8.3.3 Third Normal Form (3NF)")
    add_body_p(
        doc,
        "A relation is in 3NF if it is in 2NF and no non-prime attribute is transitively dependent on any candidate key. Two critical transitive dependencies were resolved:\n"
        "1. Company Sector: In early designs, COMPANY contained sector_name. Since ticker -> sector_name and sector_name -> sector_description, a transitive dependency existed (ticker -> sector_name -> sector_description). This was decomposed into SECTOR(sector_id, sector_name) and COMPANY(ticker, sector_id).\n"
        "2. Portfolio Holding User Redundancy: In early versions, portfolio_holding contained user_id alongside portfolio_id. Since portfolio_id -> user_id, an FD chain existed: {portfolio_id, ticker} -> portfolio_id -> user_id. In Migration 05, user_id was formally removed from portfolio_holding, ensuring pure 3NF compliance."
    )
    
    add_h3(doc, "8.3.4 Boyce-Codd Normal Form (BCNF)")
    add_body_p(
        doc,
        "A relation is in BCNF if and only if for every non-trivial functional dependency X -> Y, X is a superkey. In all normalized tables (company, sector, app_user, user_portfolio, portfolio_holding, portfolio_transaction, daily_price_history), the left-hand determinant of every valid FD is a unique candidate key. Thus, the operational transactional schema strictly satisfies BCNF."
    )
    
    add_h2(doc, "8.4 Lossless-Join Decomposition Proofs (Heath's Theorem)")
    add_body_p(
        doc,
        "Heath's Theorem states that a decomposition of relation R into R1(X, Y) and R2(X, Z) is lossless with respect to a set of functional dependencies F if and only if the common attribute set X functionally determines Y (X -> Y) or X functionally determines Z (X -> Z).\n\n"
        "Proof for Company and Daily Price History Decomposition:\n"
        "Let R = {Ticker, Date, CompanyName, Close, Volume}.\n"
        "Decomposed into R1(Ticker, CompanyName) and R2(Ticker, Date, Close, Volume).\n"
        "The common attribute set is R1 ∩ R2 = {Ticker}.\n"
        "From FD1, Ticker -> CompanyName holds in F.\n"
        "Since (R1 ∩ R2) -> (R1 - R2) = {Ticker} -> {CompanyName}, the intersection is a superkey of R1.\n"
        "Therefore, by Heath's Theorem, the natural join R1 ⨝ R2 produces exactly the original relation R with zero spurious tuples, formally proving a lossless-join decomposition."
    )
    
    add_h2(doc, "8.5 Corporate Actions: Discrete Event Extraction vs. Natural Join")
    add_body_p(
        doc,
        "An important theoretical nuance arises regarding corporate_action. Corporate actions (dividends, splits) occur on discrete, sparse trading dates (e.g., AAPL issued dividends on only 20 trading dates out of 1,259 total dates). Decomposing corporate actions into a separate table is mathematically an event extraction with horizontal filtering:\n"
        "corporate_action = π_{ticker, date, action_type, value}( σ_{Dividend > 0 ∨ SplitRatio ≠ 1}(R_UNF) )\n\n"
        "Crucially, performing a standard relational natural join (⨝) between daily_price_history and corporate_action would eradicate 98.4% of all historical trading days, because non-dividend dates have no matching tuple in corporate_action! Therefore, time-series historical price reconstruction mathematically mandates a LEFT OUTER JOIN (⟕), preserving all 287,310 daily price tuples while attaching corporate actions where existent."
    )
    
    add_h2(doc, "8.6 Anomaly Analysis in Unnormalized vs. Normalized Schemas")
    add_bullet_p(
        doc,
        " In R_UNF, if Apple Inc. updates its corporate legal name, 1,259 historical rows must be modified simultaneously. In the normalized schema, exactly 1 row in company is updated.",
        bold_prefix="Update Anomaly: "
    )
    add_bullet_p(
        doc,
        " In R_UNF, a newly incorporated company awaiting its initial public offering (IPO) cannot be inserted without manufacturing dummy historical price and date records. In normalized 3NF, the company tuple is inserted immediately into company with foreign key sector_id.",
        bold_prefix="Insertion Anomaly: "
    )
    add_bullet_p(
        doc,
        " In R_UNF, if historical price records for an inactive stock are archived or purged, the company master record and sector relationship are permanently destroyed. In normalized 3NF, purging daily_price_history leaves the company profile and sector taxonomy intact.",
        bold_prefix="Deletion Anomaly: "
    )
    
    add_h2(doc, "8.7 Intentional Analytical Denormalization: Bounded Cache in stock_summary")
    add_body_p(
        doc,
        "The relation stock_summary contains attributes (current_price, change_percent, 52w_high, 52w_low, avg_volume). Strictly speaking, each of these values can be derived through aggregate SQL queries over daily_price_history.\n"
        "However, stock_summary is intentionally maintained as a bounded analytical cache. Formally:\n"
        "1. Its candidate key is {ticker}, and its FD set is ticker -> current_price, change_percent, 52w_high, 52w_low, avg_volume. Under its own schema FD set, it strictly satisfies BCNF.\n"
        "2. It acts as an O(1) primary key lookup cache, eliminating expensive 52-week MAX(), MIN(), and AVG() aggregate scans across 287,310 rows every time the market dashboard is loaded.\n"
        "3. Synchronized via scheduled batch refresh jobs, it represents an intentional, controlled engineering optimization designed to preserve sub-10ms API latency."
    )

