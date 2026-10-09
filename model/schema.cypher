// Graph model, Neo4j 5 Community. See MODEL.md for the node and edge tables.
// Community has no existence constraints, so required properties are not enforced here.
// The data-quality checks in queries/ cover them instead.
// The constraints stand in load order: reference data, the core, the adapters, the claims.

// Reference data: the sources and our own vocabulary
CREATE CONSTRAINT source_code IF NOT EXISTS
FOR (s:Source) REQUIRE s.code IS UNIQUE;

CREATE CONSTRAINT concept_element IF NOT EXISTS
FOR (k:Concept) REQUIRE k.element IS UNIQUE;

CREATE CONSTRAINT form_type_key IF NOT EXISTS
FOR (t:FormType) REQUIRE (t.source, t.code) IS UNIQUE;

// Ring 1: axiomatic core
CREATE CONSTRAINT company_id IF NOT EXISTS
FOR (c:Company) REQUIRE c.company_id IS UNIQUE;

CREATE CONSTRAINT identifier_key IF NOT EXISTS
FOR (i:Identifier) REQUIRE (i.scheme, i.value) IS UNIQUE;

// Adapters. Each adapter node starts its key with the source.
CREATE CONSTRAINT registrant_key IF NOT EXISTS
FOR (g:Registrant) REQUIRE (g.source, g.native_id) IS UNIQUE;

CREATE CONSTRAINT fiscal_year_key IF NOT EXISTS
FOR (y:FiscalYear) REQUIRE (y.source, y.registrant, y.fiscal_year) IS UNIQUE;

CREATE CONSTRAINT fiscal_quarter_key IF NOT EXISTS
FOR (q:FiscalQuarter) REQUIRE (q.source, q.registrant, q.fiscal_year, q.quarter) IS UNIQUE;

CREATE INDEX fiscal_quarter_calendar IF NOT EXISTS
FOR (q:FiscalQuarter) ON (q.calendar_quarter);

CREATE CONSTRAINT filing_key IF NOT EXISTS
FOR (f:Filing) REQUIRE (f.source, f.native_id) IS UNIQUE;

// Claim layer reference data
CREATE CONSTRAINT exchange_mic IF NOT EXISTS
FOR (e:Exchange) REQUIRE e.mic IS UNIQUE;

CREATE CONSTRAINT industry_key IF NOT EXISTS
FOR (i:Industry) REQUIRE (i.scheme, i.code) IS UNIQUE;
