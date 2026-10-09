-- Hand-written seed: reference data and six fictional companies. fixtures/seed.cypher holds the
-- same data. The planted gaps and violations are listed in fixtures/README.md.
-- The statements stand in load order: reference data, the core, the SEC adapter, the claims.

-- 1. Reference data: the sources and our own vocabulary

-- NEWS-FEED is absent on purpose: one claim names it, and check_source_known finds that claim.
INSERT INTO source (code, name, kind) VALUES
    ('SEC',           'U.S. Securities and Exchange Commission',   'regulator'),
    ('GLEIF',         'Global Legal Entity Identifier Foundation', 'registry'),
    ('EXCHANGE-LIST', 'Listings published by the exchanges',       'exchange'),
    ('VENDOR-S2',     'Fictional data vendor',                     'vendor');

INSERT INTO concept (element, kind) VALUES
    ('Assets',      'instant'),
    ('Liabilities', 'instant'),
    ('Equity',      'instant'),
    ('Revenue',     'duration'),
    ('NetIncome',   'duration');

INSERT INTO form_type (source, code) VALUES
    ('SEC', '10-K'),
    ('SEC', '10-Q');

-- Each SEC form requires every concept.
INSERT INTO requires (source, form, element)
SELECT t.source, t.code, k.element
FROM form_type t CROSS JOIN concept k;

-- 2. Ring 1: companies and identifiers. `company_id` is our own id and carries no meaning.
-- fixtures/company_ids.json records which identifiers belong to which id.
INSERT INTO company (company_id, name, country, status) VALUES
    ('C-000001', 'Alpha Holdings Inc', 'US', 'active'),
    ('C-000002', 'Beta Corp',          'US', 'active'),
    ('C-000003', 'Gamma Ltd',          'US', 'active'),
    ('C-000004', 'Delta GmbH',         'DE', 'active'),
    ('C-000005', 'Epsilon SA',         'FR', 'active'),
    ('C-000006', 'Orphan Inc',         'US', 'active');

INSERT INTO identifier (scheme, value) VALUES
    ('LEI', '5493001ALPHAHOLD0020'),
    ('CIK', '0000000001'),
    ('LEI', '5493002BETACORP00097'),
    ('CIK', '0000000002'),
    ('CIK', '0000000003'),
    ('LEI', '5493004DELTAGMBH0018'),
    ('LEI', '5493005EPSILONSA0096'),
    ('CIK', '12AB');

-- Orphan has no identifier. Epsilon's CIK is malformed. Delta claims the CIK of Gamma.
INSERT INTO has_identifier (company_id, scheme, value, since, status, is_primary) VALUES
    ('C-000001', 'LEI', '5493001ALPHAHOLD0020', '2015-01-01', 'active', true),
    ('C-000001', 'CIK', '0000000001',           '2015-01-01', 'active', false),
    ('C-000002', 'LEI', '5493002BETACORP00097', '2015-01-01', 'active', true),
    ('C-000002', 'CIK', '0000000002',           '2015-01-01', 'active', false),
    ('C-000003', 'CIK', '0000000003',           '2015-01-01', 'active', true),
    ('C-000004', 'LEI', '5493004DELTAGMBH0018', '2015-01-01', 'active', true),
    ('C-000004', 'CIK', '0000000003',           '2015-01-01', 'active', false),
    ('C-000005', 'LEI', '5493005EPSILONSA0096', '2015-01-01', 'active', true),
    ('C-000005', 'CIK', '12AB',                 '2015-01-01', 'active', false);

-- 3. SEC adapter

-- Registrants: the companies as the SEC knows them. The core company delegates to the adapter
-- here.
INSERT INTO registrant (source, native_id, company_id, registered_name, since) VALUES
    ('SEC', '0000000001', 'C-000001', 'Alpha Holdings Inc', '2010-03-01'),
    ('SEC', '0000000002', 'C-000002', 'Beta Corp',          '2012-05-01'),
    ('SEC', '0000000003', 'C-000003', 'Gamma Ltd',          '2018-08-01');

-- Fiscal year 2024 of each registrant is the calendar year.
INSERT INTO fiscal_year (source, registrant, fiscal_year, start_date, end_date)
SELECT source, native_id, 2024, '2024-01-01', '2024-12-31'
FROM registrant
WHERE source = 'SEC';

INSERT INTO fiscal_quarter (source, registrant, fiscal_year, quarter, start_date, end_date, calendar_quarter)
SELECT y.source, y.registrant, y.fiscal_year, q.quarter, q.start_date, q.end_date,
       'Q' || q.quarter || '-2024'
FROM fiscal_year y
CROSS JOIN (VALUES
    (1, DATE '2024-01-01', DATE '2024-03-31'),
    (2, DATE '2024-04-01', DATE '2024-06-30'),
    (3, DATE '2024-07-01', DATE '2024-09-30'),
    (4, DATE '2024-10-01', DATE '2024-12-31')
) AS q (quarter, start_date, end_date);

-- Gamma's third quarter starts one day late: a planted gap after the second quarter.
UPDATE fiscal_quarter SET start_date = '2024-07-02'
WHERE source = 'SEC' AND registrant = '0000000003' AND fiscal_year = 2024 AND quarter = 3;

-- Filings. A 10-K reports on the fiscal year, a 10-Q on a quarter.
-- Beta has no 10-Q for the third quarter. Gamma has no 10-K.
INSERT INTO filing (source, native_id, registrant, form, filed_date, period_end, fiscal_year, quarter)
SELECT 'SEC', s.native_id, s.registrant, s.form, s.filed_date,
       coalesce(q.end_date, y.end_date), y.fiscal_year, s.quarter
FROM (VALUES
    ('0000000001', '0000000001-24-000001', '10-Q', 1,    DATE '2024-05-01'),
    ('0000000001', '0000000001-24-000002', '10-Q', 2,    DATE '2024-08-01'),
    ('0000000001', '0000000001-24-000003', '10-Q', 3,    DATE '2024-11-01'),
    ('0000000001', '0000000001-25-000001', '10-K', NULL, DATE '2025-02-20'),
    ('0000000002', '0000000002-24-000001', '10-Q', 1,    DATE '2024-05-02'),
    ('0000000002', '0000000002-24-000002', '10-Q', 2,    DATE '2024-08-02'),
    ('0000000002', '0000000002-25-000001', '10-K', NULL, DATE '2025-02-21'),
    ('0000000003', '0000000003-24-000001', '10-Q', 1,    DATE '2024-05-03'),
    ('0000000003', '0000000003-24-000002', '10-Q', 2,    DATE '2024-08-03'),
    ('0000000003', '0000000003-24-000003', '10-Q', 3,    DATE '2024-11-03')
) AS s (registrant, native_id, form, quarter, filed_date)
JOIN fiscal_year y ON y.source = 'SEC' AND y.registrant = s.registrant AND y.fiscal_year = 2024
LEFT JOIN fiscal_quarter q
    ON q.source = y.source AND q.registrant = y.registrant
   AND q.fiscal_year = y.fiscal_year AND q.quarter = s.quarter;

-- Every filing reports every concept, except Beta's 10-K, which omits Revenue.
INSERT INTO reports_concept (source, native_id, element, confidence)
SELECT f.source, f.native_id, k.element, 'Exact'
FROM filing f CROSS JOIN concept k
WHERE NOT (f.native_id = '0000000002-25-000001' AND k.element = 'Revenue');

-- 4. Claim layer
INSERT INTO exchange (mic, name) VALUES
    ('XNYS', 'New York Stock Exchange'),
    ('XNAS', 'Nasdaq');

INSERT INTO industry (scheme, code, name) VALUES
    ('SIC', '6719', 'Offices of Holding Companies'),
    ('SIC', '3571', 'Electronic Computers');

INSERT INTO listed_on (company_id, mic, ticker, listing_date, source, as_of, observed_at, verifiability) VALUES
    ('C-000001', 'XNYS', 'ALPH', '2010-01-04', 'EXCHANGE-LIST', '2026-01-31', '2026-02-01', 'Verified'),
    ('C-000002', 'XNAS', 'BETA', '2010-01-04', 'EXCHANGE-LIST', '2026-01-31', '2026-02-01', 'Verified');

INSERT INTO in_industry (company_id, scheme, code, source, as_of, observed_at, verifiability) VALUES
    ('C-000001', 'SIC', '6719', 'SEC', '2026-01-31', '2026-02-01', 'Verified'),
    ('C-000002', 'SIC', '3571', 'SEC', '2026-01-31', '2026-02-01', 'Verified');

-- Ownership chain: Delta -> Gamma -> Beta -> Alpha
INSERT INTO subsidiary_of (child_id, parent_id, since, source, as_of, observed_at, verifiability) VALUES
    ('C-000002', 'C-000001', '2015-01-01', 'SEC',   '2025-12-31', '2026-02-15', 'Verified'),
    ('C-000003', 'C-000002', '2015-01-01', 'SEC',   '2025-12-31', '2026-02-15', 'Verified'),
    ('C-000004', 'C-000003', '2015-01-01', 'GLEIF', '2025-12-31', '2026-02-15', 'Verified');

INSERT INTO owns_stake_in (owner_id, owned_id, percentage, source, as_of, observed_at, verifiability) VALUES
    ('C-000001', 'C-000002', 100.0, 'SEC',       '2025-12-31', '2026-02-15', 'Verified'),
    ('C-000002', 'C-000003',  75.0, 'VENDOR-S2', '2025-12-31', '2026-01-10', 'Reported'),
    ('C-000002', 'C-000003',  60.0, 'SEC',       '2026-01-31', '2026-02-05', 'Verified'),
    ('C-000002', 'C-000003',  75.0, 'VENDOR-S2', '2026-01-31', '2026-02-05', 'Reported'),
    ('C-000003', 'C-000004',  51.0, 'GLEIF',     '2026-03-01', '2026-02-01', 'Verified'),
    ('C-000001', 'C-000005', 120.0, 'NEWS-FEED', '2026-01-15', '2026-01-16', 'Alleged');
