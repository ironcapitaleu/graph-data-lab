// Graph model, Neo4j 5 Community. See MODEL.md for the node and edge tables.
// Community has no existence constraints, so required properties are not enforced here.
// The data-quality checks in queries/ cover them instead.

// Ring 1: axiomatic core
CREATE CONSTRAINT company_id IF NOT EXISTS
FOR (c:Company) REQUIRE c.company_id IS UNIQUE;

CREATE CONSTRAINT identifier_key IF NOT EXISTS
FOR (i:Identifier) REQUIRE (i.scheme, i.value) IS UNIQUE;

// Our own vocabulary and shared dimensions
CREATE CONSTRAINT concept_element IF NOT EXISTS
FOR (k:Concept) REQUIRE k.element IS UNIQUE;

CREATE CONSTRAINT period_key IF NOT EXISTS
FOR (p:Period) REQUIRE p.key IS UNIQUE;

// SEC adapter
CREATE CONSTRAINT regulator_code IF NOT EXISTS
FOR (r:Regulator) REQUIRE r.code IS UNIQUE;

CREATE CONSTRAINT registrant_key IF NOT EXISTS
FOR (g:Registrant) REQUIRE (g.regulator, g.native_id) IS UNIQUE;

CREATE CONSTRAINT fiscal_year_key IF NOT EXISTS
FOR (y:FiscalYear) REQUIRE (y.regulator, y.registrant, y.fiscal_year) IS UNIQUE;

CREATE CONSTRAINT fiscal_quarter_key IF NOT EXISTS
FOR (q:FiscalQuarter) REQUIRE (q.regulator, q.registrant, q.fiscal_year, q.quarter) IS UNIQUE;

CREATE CONSTRAINT filing_key IF NOT EXISTS
FOR (f:Filing) REQUIRE (f.regulator, f.native_id) IS UNIQUE;

CREATE CONSTRAINT form_type_key IF NOT EXISTS
FOR (t:FormType) REQUIRE (t.regulator, t.code) IS UNIQUE;

// Claim layer reference data
CREATE CONSTRAINT exchange_mic IF NOT EXISTS
FOR (e:Exchange) REQUIRE e.mic IS UNIQUE;

CREATE CONSTRAINT industry_key IF NOT EXISTS
FOR (i:Industry) REQUIRE (i.scheme, i.code) IS UNIQUE;
