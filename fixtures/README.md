# Seed Dataset

The seed has two parts. `tests/test_parity.py` fails if the two stores drift apart.

- `seed.cypher` and `seed.sql`: six fictional companies with planted gaps and violations. Real
  data has no broken identifiers and no conflicting ownership claims, so the checks need them.
- `sp500.cypher` and `sp500.sql`: 100 real S&P 500 companies from SEC EDGAR. See
  "S&P 500 companies" below.

## Companies

| Company | `company_id` | Identifiers | Files with SEC |
| --- | --- | --- | --- |
| Alpha Holdings Inc | `LEI:5493001ALPHAHOLD0020` | LEI (primary), CIK | yes |
| Beta Corp | `LEI:5493002BETACORP00097` | LEI (primary), CIK | yes |
| Gamma Ltd | `CIK:0000000003` | CIK only (no LEI fallback) | yes |
| Delta GmbH | `LEI:5493004DELTAGMBH0018` | LEI | no |
| Epsilon SA | `LEI:5493005EPSILONSA0096` | LEI (primary), malformed CIK | no |
| Orphan Inc | `TMP:orphan` | none | no |

Ownership chain (`SUBSIDIARY_OF`): Delta → Gamma → Beta → Alpha.

## Planted gaps and violations

Each row is what a query in `queries/` must find.

| What | Found by |
| --- | --- |
| Beta has no Q3-2024 10-Q | `missing_q3_2024`, `incomplete_fy2024` |
| Gamma has no FY2024 10-K | `incomplete_fy2024` |
| Beta's 10-K omits `Revenue` | `filing_missing_concepts` |
| Two claims on Beta → Gamma for 2026-01-31: 60 % and 75 % | `conflicting_ownership_claims` |
| Two claims on Beta → Gamma 75 % with different `as_of`: a time series, not a conflict | `conflicting_ownership_claims` must not report it |
| Orphan has no identifier | `check_company_has_identifier`, `check_one_primary_identifier` |
| Epsilon's CIK `12AB` is malformed | `check_identifier_format` |
| Alpha → Epsilon claim of 120 % | `check_ownership_percentage` |
| Gamma → Delta claim has `as_of` after `observed_at` | `check_claim_dates` |

## S&P 500 companies

`scripts/generate_sp500_seed.py` writes `sp500.cypher` and `sp500.sql`. Never edit them by hand.

| Data | Source | Count |
| --- | --- | --- |
| Companies | CIKs from arkad `SP500_CIKS`: arkad's 7 must-pass companies, its 3 known gaps (JPMorgan Chase, Exxon Mobil, Amazon), and an even sample of 90 more | 100 |
| Name, country, first filing date | EDGAR `submissions` | |
| Identifier | The CIK, as primary identifier. EDGAR gives no LEI, so `company_id` is `CIK:<cik>` | 100 |
| `LISTED_ON` | EDGAR tickers on NYSE, Nasdaq, and Cboe. OTC tickers are left out | 140 |
| `IN_INDUSTRY` | EDGAR SIC code | 100 |
| Filings | Each 10-K and 10-Q with a period end in 2024, with its real accession number | 398 |
| `REPORTS_CONCEPT` | EDGAR `companyfacts`: the filing holds a value for its own period end under one of arkad's US GAAP tags for the concept | 1830 |

Each claim carries `source: SEC-EDGAR`, and `as_of` and `observed_at` of 2025-12-04, the date of
the EDGAR dump. The first tag in arkad's list gives confidence `Exact`, a later tag gives `Synonym`.

A 10-Q covers the calendar quarter that holds its period end. A 10-K covers `FY2024`.

### What the real data shows

The filing questions return real companies now. Each row is true for the model as it stands, and
most rows point at a gap in the model, not in the company.

| Finding | Example | Found by |
| --- | --- | --- |
| A fiscal year that ends in Q3 has a 10-K for that quarter, not a 10-Q | Apple, Visa, Cisco, Micron, Tyson Foods | `missing_q3_2024`, `incomplete_fy2024` |
| A fiscal year that ends in another quarter leaves that calendar quarter without a 10-Q | Microsoft (Q2), NVIDIA (Q1), Target (Q1) | `incomplete_fy2024` |
| A 52-week year that ends on 2025-01-03 has no period end in 2024, so no 10-K covers `FY2024` | L3Harris, Trimble | `incomplete_fy2024` |
| Many filers never tag a bare `Liabilities` total | Amazon, 108 filings in total | `filing_missing_concepts` |
| Some filers tag net income or revenue with a tag outside arkad's list | 37 filings without `NetIncome`, 13 without `Revenue` | `filing_missing_concepts` |
