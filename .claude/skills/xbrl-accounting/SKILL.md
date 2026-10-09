---
name: xbrl-accounting
description: >
  Use when adding or changing Concept nodes, REQUIRES sets, REPORTS_CONCEPT edges, seed facts,
  or any query or check that depends on accounting meaning: SFAC 6 elements and identities,
  instant vs duration, US GAAP tags, resolution tiers, or calculation-linkbase derivations.
version: 0.1.0
---

# XBRL Accounting Domain Knowledge

## Purpose

This skill gives the accounting facts behind the lab's `Concept` nodes. It keeps seed data and
checks consistent with SFAC 6, so the lab does not model a concept that arkad cannot resolve.

Adapted from the arkad `xbrl-accounting` skill. The references are copies of arkad's files. The
FASB taxonomy XML files are not copied. Read them in arkad
(`.claude/skills/xbrl-accounting/data/taxonomy/`) or at `https://xbrl.fasb.org/us-gaap/`.

## SFAC 6 Foundation

arkad's canonical vocabulary is built on SFAC 6 (1985). Five identities must hold:

1. **Balance sheet:** Assets = Liabilities + Equity
2. **Income statement:** Net Income = Revenue − Expenses + Gains − Losses
3. **Comprehensive income:** Comprehensive Income = Net Income + OCI
4. **Changes in equity:** ΔEquity = Comprehensive Income + Investments by Owners − Distributions
5. **Cash flow:** Operating CF + Investing CF + Financing CF ≈ ΔCash

If identity 1 fails, the cause is always a bug, never valid company data.

## Procedures

### Add a Concept node

1. Check that the element exists in `references/canonical-elements.md`. Use its exact name.
2. If it does not exist, stop and ask the user. A new canonical element is an arkad decision, not
   a lab decision.
3. Set `kind` from the element: balance-sheet items are `instant`, income and cash-flow items are
   `duration`.
4. Add it to both seeds and decide which `FormType` nodes `REQUIRES` it.

### Model a derived fact

Tier 3 derives a parent from its children: `parent = Σ(child_i × weight_i)`, with weights from the
calculation linkbase (`references/calculation-linkbase.md`). In the graph this is a lineage shape,
for example `(Fact)-[:DERIVED_FROM {weight}]->(Observation)`. See arkad
`hybrid_data_model.md` §8.2 for the provenance model.

### Seed realistic numbers

If a seed holds fact values, make them satisfy the five identities. A check that tests an identity
needs one planted violation. List it in `fixtures/README.md`.

## Critical Invariants

- Never map two different concepts to the same canonical element for the same period.
- Balance-sheet items are instant. Income and cash-flow items are duration.
- Expenses are positive values that reduce net income.
- Every derived fact keeps its resolution path back to the source tags.
- An amendment supersedes the original filing.

## Authoritative Sources

- SFAC 6 elements: `references/sfac6-elements.md`
- Canonical elements: `references/canonical-elements.md`
- Resolution tiers: `references/resolution-tiers.md`
- Calculation linkbase: `references/calculation-linkbase.md`
- FASB taxonomy (live): `https://xbrl.fasb.org/us-gaap/{year}/`

## Staleness Check

`canonical-elements.md` and `resolution-tiers.md` are copies from arkad at commit `24a9849`. If
the user says arkad's element set changed, ask whether to copy the new version. If the
`taxonomy-year` in `calculation-linkbase.md` is older than the current year, tell the user that a
newer FASB taxonomy can exist.
