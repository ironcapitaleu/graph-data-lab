-- Graph model as relational tables, PostgreSQL 16. See MODEL.md for the node and edge tables.
-- Nodes are tables keyed like the graph. Edges are tables, foreign keys, or columns.
-- Data-quality rules are queries in queries/, not CHECK constraints, so the seed can hold
-- violations for the checks to find.
-- The tables stand in load order: reference data, the core, the adapters, the claims.

-- Reference data: the sources and our own vocabulary
CREATE TABLE source (
    code text PRIMARY KEY,
    name text NOT NULL,
    kind text NOT NULL -- regulator | registry | exchange | vendor
);

CREATE TABLE concept (
    element text PRIMARY KEY,
    kind    text NOT NULL -- instant | duration
);

CREATE TABLE form_type (
    source text NOT NULL REFERENCES source,
    code   text NOT NULL,
    PRIMARY KEY (source, code)
);

CREATE TABLE requires (
    source  text NOT NULL,
    form    text NOT NULL,
    element text NOT NULL REFERENCES concept,
    PRIMARY KEY (source, form, element),
    FOREIGN KEY (source, form) REFERENCES form_type
);

-- Ring 1: axiomatic core. `company_id` is our own id and carries no meaning.
CREATE TABLE company (
    company_id text PRIMARY KEY,
    name       text NOT NULL,
    country    text NOT NULL,
    status     text NOT NULL
);

CREATE TABLE identifier (
    scheme text NOT NULL,
    value  text NOT NULL,
    PRIMARY KEY (scheme, value)
);

CREATE TABLE has_identifier (
    company_id text    NOT NULL REFERENCES company,
    scheme     text    NOT NULL,
    value      text    NOT NULL,
    since      date    NOT NULL,
    status     text    NOT NULL, -- active | lapsed
    is_primary boolean NOT NULL,
    PRIMARY KEY (company_id, scheme, value),
    FOREIGN KEY (scheme, value) REFERENCES identifier
);

-- Adapters. Each adapter table starts its key with the source, so the data of two sources
-- never mixes.

-- The company as one source knows it. The core company delegates to the adapter here.
-- REGISTERED_WITH is the `company_id` column with `since`.
CREATE TABLE registrant (
    source          text NOT NULL REFERENCES source,
    native_id       text NOT NULL, -- SEC: CIK. GLEIF: LEI
    company_id      text NOT NULL REFERENCES company,
    registered_name text NOT NULL,
    since           date NOT NULL,
    -- Set only by a source that gives them (GLEIF)
    jurisdiction    text,
    status          text, -- GLEIF: ISSUED | LAPSED | ...
    next_renewal    date,
    PRIMARY KEY (source, native_id)
);

-- HAS_FISCAL_YEAR is the foreign key to `registrant`.
CREATE TABLE fiscal_year (
    source      text    NOT NULL,
    registrant  text    NOT NULL,
    fiscal_year integer NOT NULL,
    start_date  date    NOT NULL,
    end_date    date    NOT NULL,
    PRIMARY KEY (source, registrant, fiscal_year),
    FOREIGN KEY (source, registrant) REFERENCES registrant
);

-- HAS_QUARTER is the foreign key to `fiscal_year`.
CREATE TABLE fiscal_quarter (
    source           text    NOT NULL,
    registrant       text    NOT NULL,
    fiscal_year      integer NOT NULL,
    quarter          integer NOT NULL, -- 1 to 4
    start_date       date    NOT NULL,
    end_date         date    NOT NULL,
    calendar_quarter text    NOT NULL, -- e.g. Q3-2024: holds the middle day of the quarter
    PRIMARY KEY (source, registrant, fiscal_year, quarter),
    FOREIGN KEY (source, registrant, fiscal_year) REFERENCES fiscal_year
);

CREATE INDEX fiscal_quarter_calendar ON fiscal_quarter (calendar_quarter);

-- HAS_FILING is the `registrant` column.
-- REPORTS_ON is `fiscal_year` with `quarter`: a 10-K reports on the year and leaves `quarter`
-- NULL, a 10-Q reports on a quarter. Both are NULL while the period of a filing is unresolved.
CREATE TABLE filing (
    source      text NOT NULL,
    native_id   text NOT NULL,
    registrant  text NOT NULL,
    form        text NOT NULL,
    filed_date  date NOT NULL,
    period_end  date NOT NULL,
    fiscal_year integer,
    quarter     integer,
    PRIMARY KEY (source, native_id),
    FOREIGN KEY (source, form) REFERENCES form_type,
    FOREIGN KEY (source, registrant) REFERENCES registrant,
    FOREIGN KEY (source, registrant, fiscal_year) REFERENCES fiscal_year,
    FOREIGN KEY (source, registrant, fiscal_year, quarter) REFERENCES fiscal_quarter
);

CREATE TABLE reports_concept (
    source     text NOT NULL,
    native_id  text NOT NULL,
    element    text NOT NULL REFERENCES concept,
    confidence text NOT NULL, -- Exact | Synonym | Derived | Computed
    PRIMARY KEY (source, native_id, element),
    FOREIGN KEY (source, native_id) REFERENCES filing
);

-- Claim layer. Every claim carries the envelope: source, as_of, observed_at, verifiability.
-- `source` holds a code from the `source` table. It has no foreign key: `check_source_known`
-- finds a claim with an unknown source.
-- Claims are append-only, so the key includes the envelope and conflicting claims coexist.
CREATE TABLE exchange (
    mic  text PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE industry (
    scheme text NOT NULL,
    code   text NOT NULL,
    name   text NOT NULL,
    PRIMARY KEY (scheme, code)
);

CREATE TABLE listed_on (
    company_id    text NOT NULL REFERENCES company,
    mic           text NOT NULL REFERENCES exchange,
    ticker        text NOT NULL,
    listing_date  date, -- unknown when the source gives none (SEC EDGAR)
    source        text NOT NULL,
    as_of         date NOT NULL,
    observed_at   date NOT NULL,
    verifiability text NOT NULL, -- Verified | Reported | Alleged
    PRIMARY KEY (company_id, mic, ticker, source, as_of)
);

CREATE TABLE in_industry (
    company_id    text NOT NULL REFERENCES company,
    scheme        text NOT NULL,
    code          text NOT NULL,
    source        text NOT NULL,
    as_of         date NOT NULL,
    observed_at   date NOT NULL,
    verifiability text NOT NULL,
    PRIMARY KEY (company_id, scheme, code, source, as_of),
    FOREIGN KEY (scheme, code) REFERENCES industry
);

CREATE TABLE subsidiary_of (
    child_id      text NOT NULL REFERENCES company,
    parent_id     text NOT NULL REFERENCES company,
    since         date NOT NULL,
    source        text NOT NULL,
    as_of         date NOT NULL,
    observed_at   date NOT NULL,
    verifiability text NOT NULL,
    PRIMARY KEY (child_id, parent_id, source, as_of)
);

CREATE TABLE owns_stake_in (
    owner_id      text    NOT NULL REFERENCES company,
    owned_id      text    NOT NULL REFERENCES company,
    percentage    numeric NOT NULL,
    source        text    NOT NULL,
    as_of         date    NOT NULL,
    observed_at   date    NOT NULL,
    verifiability text    NOT NULL,
    PRIMARY KEY (owner_id, owned_id, source, as_of)
);
