---
name: performance
description: >
  Use when the user asks to "benchmark", "compare Neo4j and Postgres", "measure query time",
  "which store is faster", "scale up the seed", or "profile a query". Covers the method for timing
  one question on both stores and reporting the result.
version: 0.1.0
---

# Performance: Comparing the Stores

## Purpose

The lab exists partly to give evidence for arkad's deferred storage choice
(`hybrid_data_model.md` §13–§14). This skill gives the method that makes a timing worth reading.
It stores no results.

Adapted from the arkad `performance` skill.

## Current Maturity

| Capability | Status |
| --- | --- |
| Correctness on both stores | Available. `uv run pytest` |
| Generated large seed | None. The seed has 6 companies |
| Timing harness | None |
| Query plans | Available by hand: `PROFILE` in Neo4j, `EXPLAIN ANALYZE` in Postgres |

## Context Gathering

Answer these three questions before you measure. Ask the user if one is open.

1. **Goal.** Which decision does the number serve? Example: "Does a recursive CTE stay fast enough
   for ownership trees 10 levels deep?"
2. **Question.** Which folder in `queries/`?
3. **Shape of the data.** Number of companies, depth and branching of the ownership tree, number
   of filings per company. The arkad design assumes low millions of rows.

## Procedure

1. Generate a seed with the shape from step 3. Write a generator script, and load the same
   generated data into both stores. Keep the small hand-written seed for the correctness tests.
2. Confirm that the question still returns the same rows on both stores at that size. A fast wrong
   answer is not a result.
3. Warm up each store: run the query several times before you time it.
4. Time many runs and report the median and the 95th percentile, not one run.
5. Read the plan on both stores (`PROFILE`, `EXPLAIN ANALYZE`). Check that the plan uses the
   indexes you expect. A missing index makes the comparison unfair.
6. Report: the numbers, the data shape, the machine, the store versions, and the date. Then say
   what the numbers mean for the goal.

## Critical Invariants

- Never compare a timing from a 6-company seed. It measures driver overhead, not the store.
- Both stores get the same data and the same index coverage. If one side lacks an index, the
  comparison is invalid.
- State the machine and the date with every number. Docker on a laptop and a server are not
  comparable.
- Results do not go in this skill. Put durable findings in a findings document, for example
  `findings/<date>-<topic>.md`, and offer the user to port them to arkad §13.

## Self-Improvement

When the team adopts a timing harness or a generator, update the maturity table. Ask the user
before you change this skill.
