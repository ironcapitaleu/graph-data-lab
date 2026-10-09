# Seed Dataset

The seed has two parts. `tests/test_parity.py` fails if the two stores drift apart.

- `seed.cypher` and `seed.sql`: the reference data and six fictional companies with planted gaps
  and violations. Real data has no broken identifiers and no conflicting ownership claims, so
  the checks need them.
- `sp500.cypher` and `sp500.sql`: 100 real S&P 500 companies from SEC EDGAR and GLEIF. See
  "S&P 500 companies" below.

`scripts/load_stores.py` loads the files in this order: `model/schema`, `fixtures/seed`,
`fixtures/sp500`. Inside each file the order is: reference data, the core, the adapters, the
claims.

`company_ids.json` records our id of each company and the identifiers that lead to it. The
generator reads it and adds new companies, so a company keeps its id for good. Never change or
reuse an id in this file.

## Reference data

| Source | Kind |
| --- | --- |
| `SEC` | regulator |
| `GLEIF` | registry |
| `EXCHANGE-LIST` | exchange |
| `VENDOR-S2` | vendor (fictional) |

## Companies

| Company | `company_id` | Identifiers | Registered with SEC |
| --- | --- | --- | --- |
| Alpha Holdings Inc | `C-000001` | LEI (primary), CIK | yes |
| Beta Corp | `C-000002` | LEI (primary), CIK | yes |
| Gamma Ltd | `C-000003` | CIK only | yes |
| Delta GmbH | `C-000004` | LEI (primary), and the CIK of Gamma | no |
| Epsilon SA | `C-000005` | LEI (primary), malformed CIK | no |
| Orphan Inc | `C-000006` | none | no |

Ownership chain (`SUBSIDIARY_OF`): Delta → Gamma → Beta → Alpha.

## Planted gaps and violations

Each row is what a query in `queries/` must find.

| What | Found by |
| --- | --- |
| Beta has no 10-Q for the third quarter of fiscal 2024 | `missing_q3_2024`, `incomplete_fy2024` |
| Gamma has no 10-K for fiscal 2024 | `incomplete_fy2024` |
| Gamma's third quarter starts on 2024-07-02, one day after the day it must start | `check_fiscal_quarters` |
| Beta's 10-K omits `Revenue` | `filing_missing_concepts` |
| Two claims on Beta → Gamma for 2026-01-31: 60 % and 75 % | `conflicting_ownership_claims` |
| Two claims on Beta → Gamma 75 % with different `as_of`: a time series, not a conflict | `conflicting_ownership_claims` must not report it |
| Orphan has no identifier | `check_company_has_identifier`, `check_one_primary_identifier` |
| Epsilon's CIK `12AB` is malformed | `check_identifier_format` |
| Alpha → Epsilon claim of 120 % | `check_ownership_percentage` |
| The same claim names the source `NEWS-FEED`, which the source list does not hold | `check_source_known` |
| Delta holds the CIK `0000000003`, which belongs to Gamma | `check_identifier_one_company` |
| Gamma → Delta claim has `as_of` after `observed_at` | `check_claim_dates` |

## S&P 500 companies

`scripts/generate_sp500_seed.py` writes `sp500.cypher` and `sp500.sql`. Never edit them by hand.

| Data | Source | Count |
| --- | --- | --- |
| Companies | CIKs from arkad `SP500_CIKS`: arkad's 7 must-pass companies, its 3 known gaps (JPMorgan Chase, Exxon Mobil, Amazon), and an even sample of 90 more | 100 |
| Name, country, first filing date | EDGAR `submissions` | |
| `company_id` | Our own id, `C-000007` to `C-000106`, from `company_ids.json` | 100 |
| Identifier | The CIK, as primary identifier | 100 |
| `Registrant` (SEC) | One per company, keyed by CIK | 100 |
| `Registrant` (GLEIF) and LEI identifier | One per company that `scripts/fetch_gleif.py` matched, keyed by LEI. See "GLEIF records" below | 94 |
| `FiscalYear` | Fiscal year 2024, with the dates of the 10-K that declares it | 99 |
| `FiscalQuarter` | Four per fiscal year. The first three take their dates from the 10-Q | 396 |
| Filings | The 10-K and each 10-Q of fiscal 2024, with the real accession number | 399 |
| `REPORTS_CONCEPT` | EDGAR `companyfacts`: the filing holds a value for its own period end under one of arkad's US GAAP tags for the concept | 1840 |
| `LISTED_ON` | EDGAR tickers on NYSE, Nasdaq, and Cboe. OTC tickers are left out | 140 |
| `IN_INDUSTRY` | EDGAR SIC code | 100 |

Each claim carries `source: SEC`, and `as_of` and `observed_at` of 2025-12-04, the date of
the EDGAR dump. The first tag in arkad's list gives confidence `Exact`, a later tag gives `Synonym`.

### How a fiscal period gets its dates

- Each fact in EDGAR carries the fiscal year and fiscal period that its filing declares (`fy`,
  `fp`), and the first and last day of its value.
- The 10-K that declares fiscal year 2024 gives the year. Its facts with a length of about one
  year give the start date.
- Each 10-Q that declares `Q1`, `Q2`, or `Q3` of fiscal 2024 gives one quarter. Its facts with a
  length of about three months give the start date.
- The fourth quarter runs from the day after the third quarter to the end of the year.
- If no 10-Q declares a quarter, the quarter fills the space between its neighbors and has no
  filing.

### GLEIF records

GLEIF does not know the CIK, so no shared key connects an EDGAR company to its LEI record.
`scripts/fetch_gleif.py` searches the GLEIF API by name and accepts a record only if all of this
holds:

- The LEI has valid check digits and the entity is active.
- The name has the same words as the EDGAR name, in any order and with any legal suffix form.
- One more fact matches: the jurisdiction of incorporation, or the postal code or city of the
  headquarters.
- Exactly one record passes.

`fixtures/gleif_records.json` holds the accepted record per CIK with the facts it matched on, and
the six companies that got no LEI. Each matched company gets an `Identifier (LEI)` and a second
`Registrant` with `source: GLEIF`. The `company_id` does not change when the LEI arrives.

| Finding | Detail |
| --- | --- |
| 94 of 100 companies match | 70 on name, jurisdiction, and postal code. 24 on name and one more fact |
| 6 companies get no LEI | Amazon, PayPal, Applied Materials, O'Reilly, Willis Towers Watson: no record passes. Public Storage: two records pass |
| 11 of 94 LEIs lapsed | The company did not renew the registration. Host Hotels lapsed in 2014, Meta in September 2026 |
| The two sources spell 61 of 94 names differently | EDGAR: `SCHWAB CHARLES CORP`. GLEIF: `THE CHARLES SCHWAB CORPORATION` |
| arkad's key rule would give 94 companies a new `company_id` | The key changes from `CIK:…` to `LEI:…` on the day the LEI arrives. The lab's own id stays |

### What the real data shows

| Finding | Example | Found by |
| --- | --- | --- |
| With fiscal periods, no real company misses its third quarter. With calendar periods, 7 did | Apple, Visa, Cisco | `missing_q3_2024` |
| The quarters of all 99 fiscal years follow each other with no gap, by the dates in the filings alone | | `check_fiscal_quarters` |
| A filing can declare the wrong fiscal period (see the figure in `model/MODEL.md` §5.5). AES tagged its 10-Q for March 2024 as `Q2` of fiscal 2022. Electronic Arts tagged its 10-Q for June 2023 as fiscal 2023, not 2024 | AES, Electronic Arts | `check_filing_has_period`, `incomplete_fy2024` |
| The dump holds no facts for one 10-K, so the company has no fiscal year and its three 10-Qs report on nothing | S&P Global | `check_filing_has_period` |
| "Fiscal 2024" is a label, not a date range. It ends between January 2024 and February 2025 | NVIDIA (2024-01-28), Target (2025-02-01) | |
| Many filers never tag a bare `Liabilities` total | Amazon | `filing_missing_concepts` |
