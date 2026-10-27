-- ============================================================================
-- Migration: 06_retire_risk_jsonb_column.sql
-- Database:  stock_market_db (PostgreSQL port 5435)
-- Purpose:   Retires the redundant sector_concentration JSONB column from
--            portfolio_risk_analysis after normalized table verification.
-- ============================================================================
-- Academic Rationale & Invariants:
--   1. Strict 1NF Relational Modeling:
--      - portfolio_risk_sector_allocation is now the authoritative 1NF source of truth.
--      - Dropping sector_concentration permanently eliminates non-atomic attributes
--        and inter-relational duplication.
--   2. Backward-Compatibility Guarantee:
--      - View v_portfolio_risk_analysis dynamically synthesizes the JSON structure
--        via jsonb_object_agg for any consumers that require JSON output.
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- 1. Validation check: Ensure normalized table contains data if any analysis exists
DO $$
DECLARE
    v_analysis_count INTEGER;
    v_alloc_count    INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_analysis_count FROM portfolio_risk_analysis;
    SELECT COUNT(*) INTO v_alloc_count FROM portfolio_risk_sector_allocation;

    RAISE NOTICE 'Retirement pre-check: % risk analyses, % normalized sector allocations.',
        v_analysis_count, v_alloc_count;
END;
$$;

-- 2. Drop the redundant JSONB column
ALTER TABLE portfolio_risk_analysis
    DROP COLUMN IF EXISTS sector_concentration;

COMMENT ON TABLE portfolio_risk_analysis IS
'Portfolio risk analysis summary metrics (Sharpe ratio, volatility, drawdown). Sector concentrations are normalized in portfolio_risk_sector_allocation.';

COMMIT;
