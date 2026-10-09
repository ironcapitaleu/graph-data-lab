// Seed dataset. Fictional companies. fixtures/seed.sql holds the same data.
// The planted gaps and violations are listed in fixtures/README.md.

// Ring 1: companies and identifiers
UNWIND [
  {id: 'LEI:5493001ALPHAHOLD0020', name: 'Alpha Holdings Inc', country: 'US'},
  {id: 'LEI:5493002BETACORP00097', name: 'Beta Corp',          country: 'US'},
  {id: 'CIK:0000000003',           name: 'Gamma Ltd',          country: 'US'},
  {id: 'LEI:5493004DELTAGMBH0018', name: 'Delta GmbH',         country: 'DE'},
  {id: 'LEI:5493005EPSILONSA0096', name: 'Epsilon SA',         country: 'FR'},
  {id: 'TMP:orphan',               name: 'Orphan Inc',         country: 'US'}
] AS row
CREATE (:Company {company_id: row.id, name: row.name, country: row.country, status: 'active'});

UNWIND [
  {company: 'LEI:5493001ALPHAHOLD0020', scheme: 'LEI', value: '5493001ALPHAHOLD0020', primary: true},
  {company: 'LEI:5493001ALPHAHOLD0020', scheme: 'CIK', value: '0000000001',           primary: false},
  {company: 'LEI:5493002BETACORP00097', scheme: 'LEI', value: '5493002BETACORP00097', primary: true},
  {company: 'LEI:5493002BETACORP00097', scheme: 'CIK', value: '0000000002',           primary: false},
  {company: 'CIK:0000000003',           scheme: 'CIK', value: '0000000003',           primary: true},
  {company: 'LEI:5493004DELTAGMBH0018', scheme: 'LEI', value: '5493004DELTAGMBH0018', primary: true},
  {company: 'LEI:5493005EPSILONSA0096', scheme: 'LEI', value: '5493005EPSILONSA0096', primary: true},
  {company: 'LEI:5493005EPSILONSA0096', scheme: 'CIK', value: '12AB',                 primary: false}
] AS row
MATCH (c:Company {company_id: row.company})
CREATE (i:Identifier {scheme: row.scheme, value: row.value})
CREATE (c)-[:HAS_IDENTIFIER {since: date('2015-01-01'), status: 'active', primary: row.primary}]->(i);

// Vocabulary and shared dimensions
UNWIND [
  {element: 'Assets',      kind: 'instant'},
  {element: 'Liabilities', kind: 'instant'},
  {element: 'Equity',      kind: 'instant'},
  {element: 'Revenue',     kind: 'duration'},
  {element: 'NetIncome',   kind: 'duration'}
] AS row
CREATE (:Concept {element: row.element, kind: row.kind});

UNWIND [
  {key: 'Q1-2024', kind: 'quarter',     start: '2024-01-01', end: '2024-03-31'},
  {key: 'Q2-2024', kind: 'quarter',     start: '2024-04-01', end: '2024-06-30'},
  {key: 'Q3-2024', kind: 'quarter',     start: '2024-07-01', end: '2024-09-30'},
  {key: 'Q4-2024', kind: 'quarter',     start: '2024-10-01', end: '2024-12-31'}
] AS row
CREATE (:Period {key: row.key, kind: row.kind, start_date: date(row.start), end_date: date(row.end)});

// GLEIF is a registry, not a regulator. The node label is the same for both.
CREATE (:Regulator {code: 'GLEIF', name: 'Global Legal Entity Identifier Foundation'});

// SEC adapter
CREATE (sec:Regulator {code: 'SEC', name: 'U.S. Securities and Exchange Commission'})
WITH sec
UNWIND ['10-K', '10-Q'] AS form
CREATE (t:FormType {regulator: 'SEC', code: form})
WITH t
MATCH (k:Concept)
CREATE (t)-[:REQUIRES]->(k);

// Registrants: the companies as the SEC knows them. The core company delegates to the adapter here.
UNWIND [
  {company: 'LEI:5493001ALPHAHOLD0020', cik: '0000000001', name: 'Alpha Holdings Inc', first: '2010-03-01'},
  {company: 'LEI:5493002BETACORP00097', cik: '0000000002', name: 'Beta Corp',          first: '2012-05-01'},
  {company: 'CIK:0000000003',           cik: '0000000003', name: 'Gamma Ltd',          first: '2018-08-01'}
] AS row
MATCH (c:Company {company_id: row.company}), (r:Regulator {code: 'SEC'})
CREATE (g:Registrant {regulator: 'SEC', native_id: row.cik, name: row.name})
CREATE (c)-[:REGISTERED_AS]->(g)
CREATE (g)-[:FILES_WITH {first_filed: date(row.first)}]->(r);

// Fiscal year 2024 of each registrant is the calendar year. `name` is the caption in the
// Neo4j Browser.
MATCH (g:Registrant)
CREATE (g)-[:HAS_FISCAL_YEAR]->(:FiscalYear {regulator: 'SEC', registrant: g.native_id,
  fiscal_year: 2024, start_date: date('2024-01-01'), end_date: date('2024-12-31'), name: 'FY2024'});

UNWIND [
  {quarter: 1, start: '2024-01-01', end: '2024-03-31'},
  {quarter: 2, start: '2024-04-01', end: '2024-06-30'},
  {quarter: 3, start: '2024-07-01', end: '2024-09-30'},
  {quarter: 4, start: '2024-10-01', end: '2024-12-31'}
] AS row
MATCH (y:FiscalYear), (p:Period {key: 'Q' + toString(row.quarter) + '-2024'})
CREATE (y)-[:HAS_QUARTER]->(q:FiscalQuarter {regulator: 'SEC', registrant: y.registrant,
  fiscal_year: 2024, quarter: row.quarter, start_date: date(row.start), end_date: date(row.end),
  name: 'Q' + toString(row.quarter)})
CREATE (q)-[:ALIGNS_WITH]->(p);

// Gamma's third quarter starts one day late: a planted gap after the second quarter.
MATCH (q:FiscalQuarter {registrant: '0000000003', fiscal_year: 2024, quarter: 3})
SET q.start_date = date('2024-07-02');

// Filings. A 10-K reports on the fiscal year, a 10-Q on a quarter.
// Beta has no 10-Q for the third quarter. Gamma has no 10-K.
UNWIND [
  {cik: '0000000001', id: '0000000001-24-000001', form: '10-Q', quarter: 1,    filed: '2024-05-01'},
  {cik: '0000000001', id: '0000000001-24-000002', form: '10-Q', quarter: 2,    filed: '2024-08-01'},
  {cik: '0000000001', id: '0000000001-24-000003', form: '10-Q', quarter: 3,    filed: '2024-11-01'},
  {cik: '0000000001', id: '0000000001-25-000001', form: '10-K', quarter: null, filed: '2025-02-20'},
  {cik: '0000000002', id: '0000000002-24-000001', form: '10-Q', quarter: 1,    filed: '2024-05-02'},
  {cik: '0000000002', id: '0000000002-24-000002', form: '10-Q', quarter: 2,    filed: '2024-08-02'},
  {cik: '0000000002', id: '0000000002-25-000001', form: '10-K', quarter: null, filed: '2025-02-21'},
  {cik: '0000000003', id: '0000000003-24-000001', form: '10-Q', quarter: 1,    filed: '2024-05-03'},
  {cik: '0000000003', id: '0000000003-24-000002', form: '10-Q', quarter: 2,    filed: '2024-08-03'},
  {cik: '0000000003', id: '0000000003-24-000003', form: '10-Q', quarter: 3,    filed: '2024-11-03'}
] AS row
MATCH (g:Registrant {regulator: 'SEC', native_id: row.cik})-[:HAS_FISCAL_YEAR]->(y:FiscalYear {fiscal_year: 2024}),
      (t:FormType {regulator: 'SEC', code: row.form})
OPTIONAL MATCH (y)-[:HAS_QUARTER]->(q:FiscalQuarter {quarter: row.quarter})
WITH g, t, row, coalesce(q, y) AS reported
CREATE (f:Filing {regulator: 'SEC', native_id: row.id, form: row.form,
                  filed_date: date(row.filed), period_end: reported.end_date})
CREATE (g)-[:HAS_FILING]->(f)
CREATE (f)-[:OF_FORM]->(t)
CREATE (f)-[:REPORTS_ON]->(reported);

// Every filing reports every concept, except Beta's 10-K, which omits Revenue.
MATCH (f:Filing), (k:Concept)
WHERE NOT (f.native_id = '0000000002-25-000001' AND k.element = 'Revenue')
CREATE (f)-[:REPORTS_CONCEPT {confidence: 'Exact'}]->(k);

// Claim layer
CREATE (:Exchange {mic: 'XNYS', name: 'New York Stock Exchange'});
CREATE (:Exchange {mic: 'XNAS', name: 'Nasdaq'});
CREATE (:Industry {scheme: 'SIC', code: '6719', name: 'Offices of Holding Companies'});
CREATE (:Industry {scheme: 'SIC', code: '3571', name: 'Electronic Computers'});

UNWIND [
  {company: 'LEI:5493001ALPHAHOLD0020', mic: 'XNYS', ticker: 'ALPH'},
  {company: 'LEI:5493002BETACORP00097', mic: 'XNAS', ticker: 'BETA'}
] AS row
MATCH (c:Company {company_id: row.company}), (e:Exchange {mic: row.mic})
CREATE (c)-[:LISTED_ON {ticker: row.ticker, listing_date: date('2010-01-04'),
                        source: 'EXCHANGE-LIST', as_of: date('2026-01-31'),
                        observed_at: date('2026-02-01'), verifiability: 'Verified'}]->(e);

UNWIND [
  {company: 'LEI:5493001ALPHAHOLD0020', code: '6719'},
  {company: 'LEI:5493002BETACORP00097', code: '3571'}
] AS row
MATCH (c:Company {company_id: row.company}), (i:Industry {scheme: 'SIC', code: row.code})
CREATE (c)-[:IN_INDUSTRY {source: 'SEC-EDGAR', as_of: date('2026-01-31'),
                          observed_at: date('2026-02-01'), verifiability: 'Verified'}]->(i);

// Ownership chain: Delta -> Gamma -> Beta -> Alpha
UNWIND [
  {child: 'LEI:5493002BETACORP00097', parent: 'LEI:5493001ALPHAHOLD0020', source: 'SEC-10K-EX21'},
  {child: 'CIK:0000000003',           parent: 'LEI:5493002BETACORP00097', source: 'SEC-10K-EX21'},
  {child: 'LEI:5493004DELTAGMBH0018', parent: 'CIK:0000000003',           source: 'GLEIF-L2'}
] AS row
MATCH (c:Company {company_id: row.child}), (p:Company {company_id: row.parent})
CREATE (c)-[:SUBSIDIARY_OF {since: date('2015-01-01'), source: row.source,
                            as_of: date('2025-12-31'), observed_at: date('2026-02-15'),
                            verifiability: 'Verified'}]->(p);

UNWIND [
  {owner: 'LEI:5493001ALPHAHOLD0020', owned: 'LEI:5493002BETACORP00097', pct: 100.0, source: 'SEC-10K-EX21', as_of: '2025-12-31', observed: '2026-02-15', ver: 'Verified'},
  {owner: 'LEI:5493002BETACORP00097', owned: 'CIK:0000000003',           pct: 75.0,  source: 'VENDOR-S2',    as_of: '2025-12-31', observed: '2026-01-10', ver: 'Reported'},
  {owner: 'LEI:5493002BETACORP00097', owned: 'CIK:0000000003',           pct: 60.0,  source: 'SEC-13D-S1',   as_of: '2026-01-31', observed: '2026-02-05', ver: 'Verified'},
  {owner: 'LEI:5493002BETACORP00097', owned: 'CIK:0000000003',           pct: 75.0,  source: 'VENDOR-S2',    as_of: '2026-01-31', observed: '2026-02-05', ver: 'Reported'},
  {owner: 'CIK:0000000003',           owned: 'LEI:5493004DELTAGMBH0018', pct: 51.0,  source: 'GLEIF-L2',     as_of: '2026-03-01', observed: '2026-02-01', ver: 'Verified'},
  {owner: 'LEI:5493001ALPHAHOLD0020', owned: 'LEI:5493005EPSILONSA0096', pct: 120.0, source: 'NEWS-FEED',    as_of: '2026-01-15', observed: '2026-01-16', ver: 'Alleged'}
] AS row
MATCH (o:Company {company_id: row.owner}), (t:Company {company_id: row.owned})
CREATE (o)-[:OWNS_STAKE_IN {percentage: row.pct, source: row.source, as_of: date(row.as_of),
                            observed_at: date(row.observed), verifiability: row.ver}]->(t);
