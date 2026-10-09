-- Graph model as relational tables, PostgreSQL 16. See MODEL.md for the node and edge tables.
-- Nodes are tables keyed like the graph. Edges are tables with the endpoint keys as columns.
-- Data-quality rules are queries in queries/, not CHECK constraints, so the seed can hold
-- violations for the checks to find.

-- Ring 1: axiomatic core
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
    status     text    NOT NULL,
    is_primary boolean NOT NULL,
    PRIMARY KEY (company_id, scheme, value),
    FOREIGN KEY (scheme, value) REFERENCES identifier
);

-- Our own vocabulary and shared dimensions
CREATE TABLE concept (
    element text PRIMARY KEY,
    kind    text NOT NULL -- instant | duration
);

CREATE TABLE period (
    key        text PRIMARY KEY,
    kind       text NOT NULL, -- quarter | fiscal_year
    start_date date NOT NULL,
    end_date   date NOT NULL
);

-- SEC adapter
CREATE TABLE regulator (
    code text PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE form_type (
    regulator text NOT NULL REFERENCES regulator,
    code      text NOT NULL,
    PRIMARY KEY (regulator, code)
);

CREATE TABLE requires (
    regulator text NOT NULL,
    form      text NOT NULL,
    element   text NOT NULL REFERENCES concept,
    PRIMARY KEY (regulator, form, element),
    FOREIGN KEY (regulator, form) REFERENCES form_type
);

-- FILED_UNDER is the `regulator` column. The form link is the `form` column.
CREATE TABLE filing (
    regulator  text NOT NULL REFERENCES regulator,
    native_id  text NOT NULL,
    form       text NOT NULL,
    filed_date date NOT NULL,
    period_end date NOT NULL,
    PRIMARY KEY (regulator, native_id),
    FOREIGN KEY (regulator, form) REFERENCES form_type
);

CREATE TABLE has_filing (
    company_id text NOT NULL REFERENCES company,
    regulator  text NOT NULL,
    native_id  text NOT NULL,
    PRIMARY KEY (company_id, regulator, native_id),
    FOREIGN KEY (regulator, native_id) REFERENCES filing
);

CREATE TABLE files_with (
    company_id  text NOT NULL REFERENCES company,
    regulator   text NOT NULL REFERENCES regulator,
    first_filed date NOT NULL,
    PRIMARY KEY (company_id, regulator)
);

CREATE TABLE covers_period (
    regulator  text NOT NULL,
    native_id  text NOT NULL,
    period_key text NOT NULL REFERENCES period,
    PRIMARY KEY (regulator, native_id, period_key),
    FOREIGN KEY (regulator, native_id) REFERENCES filing
);

CREATE TABLE reports_concept (
    regulator  text NOT NULL,
    native_id  text NOT NULL,
    element    text NOT NULL REFERENCES concept,
    confidence text NOT NULL, -- Exact | Synonym | Derived | Computed
    PRIMARY KEY (regulator, native_id, element),
    FOREIGN KEY (regulator, native_id) REFERENCES filing
);

-- Claim layer. Every claim carries the envelope: source, as_of, observed_at, verifiability.
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
    listing_date  date NOT NULL,
    source        text NOT NULL,
    as_of         date NOT NULL,
    observed_at   date NOT NULL,
    verifiability text NOT NULL, -- Verified | Reported | Alleged
    PRIMARY KEY (company_id, mic, source, as_of)
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
