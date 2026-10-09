# Seed Dataset

`seed.cypher` and `seed.sql` load the same fictional data. `tests/test_parity.py` fails if the
two drift apart.

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
