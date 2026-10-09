---
name: lab-testing
description: >
  Use when adding a question to queries/, changing a seed, writing or reviewing a test, or when
  a test fails. Covers the query-pair convention, planted violations, seed parity, and how to
  prove that a test can fail.
version: 0.1.0
---

# Lab Testing

## Purpose

Every result in the lab is evidence about the model or about a store. A test that passes for the
wrong reason produces false evidence. This skill gives the rules that keep each test honest.

Adapted from the arkad `testing` skill. The Rust-specific parts are removed.

## How the Tests Work

- `tests/conftest.py` wipes both databases, then loads `model/schema.*`, `fixtures/seed.*`, and
  `fixtures/sp500.*`.
- `tests/test_queries.py` runs each `queries/<name>/query.cypher` on Neo4j and each `query.sql` on
  Postgres. Both results must equal `expected.json`. Row order does not count.
- `tests/test_parity.py` compares node and edge counts between the two seeds.

## Procedures

### Add a question

1. Write the question as one sentence. If it needs "and", make two questions.
2. Decide which seed rows the answer depends on. If no row exercises the question, add one to both
   seeds and list it in `fixtures/README.md`.
3. Add a row that the query must *not* return, when the question has a near miss. Example: the
   same `as_of` is a conflict, but a different `as_of` is a time series.
4. Write `query.cypher` and `query.sql`. Use the same column names. Return dates as text
   (`toString(...)`, `::text`) and avoid floats, so the two drivers return equal values.
5. Write `expected.json` by hand from the seed. Never copy it from a query result. If the answer
   includes S&P 500 companies, derive those rows in `scripts/generate_sp500_seed.py` from the
   EDGAR files, and check three of them by hand.
6. Run `uv run pytest`. If you changed a file in `tests/`, run all pre-push checks from
   `AGENTS.md`.
7. Prove that the test can fail: change `expected.json` once, run the tests, see both go red, then
   restore it.

### Add a data-quality check

Name it `check_<rule>`. It returns the rows that break the rule, so an empty result means "clean".
The seed must hold at least one planted violation, or the check proves nothing.

### Change a seed

Change `seed.cypher` and `seed.sql` in the same commit. If a new node label or edge type appears,
add a count pair to `tests/test_parity.py`.

### When a test fails

1. Run the query by hand in the Neo4j Browser or `psql` and read the rows.
2. Decide which side is wrong: the query, the seed, or `expected.json`.
3. If only one store fails, compare the two queries first. A semantic gap between Cypher and SQL is
   a finding, not noise. Record it in the commit message.

## Critical Invariants

- One `expected.json` per question, shared by both stores.
- Write the expected rows from the seed, never from a query result.
- Every check has a planted violation.
- Every new test failed once on purpose before you trust it.
- Never weaken an expected result to make a test pass. Find the cause.

## Self-Improvement

If a test passes for the wrong reason, or a Cypher and SQL difference surprises you, ask the user
whether to add the trap to this skill.
