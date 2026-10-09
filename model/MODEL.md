# Graph Model — Working Copy

> Copied from arkad `sec/design/data_model/hybrid_data_model.md` §5 at commit `24a9849`.
> This copy belongs to the lab. Change it freely here. If a change proves useful, port it back to
> arkad in a normal PR.
>
> Lab additions not in the arkad doc:
>
> - `FormType` node and `REQUIRES` edge. They hold the expected-concept set per form, which the
>   `REPORTS_CONCEPT` completeness check needs.
> - `HAS_IDENTIFIER.primary` flag. The "exactly one primary id" check needs it.
> - `LISTED_ON.listing_date` is optional. SEC EDGAR gives the ticker and the exchange of a
>   listing, but no listing date.
> - The ticker is part of the `LISTED_ON` key. A company can list several securities on one
>   exchange, for example Alphabet with `GOOG` and `GOOGL`.
> - An explicit adapter layer under the core company: `Registrant`, `FiscalYear`, and
>   `FiscalQuarter`. See "5.5 The adapter layer" below. It replaces `COVERS_PERIOD`,
>   `FILED_UNDER`, and the edges from `Company` to `Filing` and to `Regulator`.
> - `company_id` is our own id with no meaning, for example `C-000007`. arkad derives it from
>   the LEI, with the CIK as fallback. See "5.6 Company identity" below.
> - `Regulator` is now `Source`, with a `kind`. Claims and adapter nodes name it by its code.
> - No node for a shared label. `Period`, `ALIGNS_WITH`, `OF_FORM`, and the edge from a
>   registrant to its source are gone. See "5.7 Node or property" below.

## 5. Universal Knowledge Graph (Knowledge-Base Layer)

Models **identity, structure, and relationships** for every company worldwide. Reworked per
PR review (2026-08-08): built **from the minimal axiomatic core outward** — start with the
non-negotiables that hold for *every company ever*, then the SEC adapter, then the bridge
between them. Everything not independently verifiable (classifications, relationships) enters
as a **source-attributed claim** (§5.2), never as core truth. Keep the model minimal but
extensible.

### 5.1 Nodes — three rings

| Node | Ring | Key | Notes |
| --- | --- | --- | --- |
| `Company` | **core — axiomatic** | `company_id`: our own id, no meaning (§5.6) | *the* non-negotiable node; entity_name, country, status |
| `Identifier` | **core — axiomatic** | `(scheme, value)` e.g. `(LEI, …)`, `(CIK, …)` | identity records attached to `Company`; each verifiable against its issuing registry (GLEIF, EDGAR) |
| `Concept` | core — ours by construction | `CanonicalElement` | our own vocabulary — axiomatic because *we* define it (enables "which concepts expected/missing") |
| `Source` | reference data | `code` (SEC, GLEIF, a vendor) | name, kind (regulator, registry, exchange, vendor). A list to look up, with no edges (§5.7) |
| `FormType` | reference data | `source + code` (SEC, 10-K) | carries `REQUIRES` to the concepts a form must report |
| `Registrant` | adapter | `source + native_id` (SEC: CIK, GLEIF: LEI) | the company as one source knows it; the root of everything the adapter holds for a company (§5.5). registered_name, and what only some sources give: jurisdiction, status, next_renewal |
| `FiscalYear` | adapter | `source + registrant + fiscal_year` | start_date, end_date as the 10-K declares them |
| `FiscalQuarter` | adapter | `… + quarter` (1 to 4) | start_date, end_date, calendar_quarter; the fourth quarter has no filing of its own |
| `Filing` | adapter | `source + native_id` (SEC: accession) | form, filed_date, period_end, taxonomy version |
| `Exchange` | reference data | `mic` (ISO 10383) | the *list* is a verifiable standard; any given *listing* is a claim (§5.2) |
| `Industry`/`Sector` | **claim layer — not core** | `scheme+code` (GICS/SIC/NACE) | classifications are source-owned opinions (GICS is S&P/MSCI's, SIC is the SEC's), multi-label, and disagree across schemes — attached only via source-attributed `IN_INDUSTRY` claims |

**Build order (review directive):** reference data (`Source`, `Concept`, `FormType`) → ring 1
(`Company` + `Identifier`) → the adapters (`Registrant`, fiscal periods, `Filing` + structural
edges), each joined to the core by the bridge `REGISTERED_WITH` (CIK→`CompanyId` resolution,
§11) → the claim layer, as its sources are onboarded. The seed files and
`scripts/load_stores.py` follow this order.

### 5.2 Edges — structural vs claims

**Structural edges** — adapter-verifiable (a filing either exists in EDGAR or it doesn't):

| Edge | From → To | Properties |
| --- | --- | --- |
| `HAS_IDENTIFIER` | Company → Identifier | since, status (active / lapsed) |
| `REGISTERED_WITH` | Company → Registrant | since. The bridge from the core to an adapter (CIK → `CompanyId` resolution, §11) |
| `HAS_FILING` | Registrant → Filing | |
| `HAS_FISCAL_YEAR` | Registrant → FiscalYear | |
| `HAS_QUARTER` | FiscalYear → FiscalQuarter | |
| `REPORTS_ON` | Filing → FiscalYear or FiscalQuarter | a 10-K reports on the year, a 10-Q on a quarter; absent while the period is unresolved |
| `REQUIRES` | FormType → Concept | the concepts a form must report |
| `REPORTS_CONCEPT` | Filing → Concept | resolved confidence (structural completeness) |

**Relationship edges — source-attributed claims.** A relationship assertion is only as good
as its source, and sources disagree: `A OWNS_STAKE_IN B: 42% as of 2026-01-31 per S1` can
coexist with `… 53% as of 2026-01-16 per S2` (different `as_of` — a legitimate time series,
not a conflict) *and* with `… 53% as of 2026-01-31 per S2` (same `as_of` — a genuine
conflict). So every relationship edge carries a uniform **claim envelope** beside its payload:

- `source` — the code of the `Source` that asserted it (provenance, §8.2)
- `as_of` — the date the assertion is *about*; `observed_at` — when we ingested it
- `verifiability` — `Verified` (regulatory filing / official registry) · `Reported`
  (reputable aggregator or data vendor) · `Alleged` (news, unconfirmed)

| Edge (claim) | From → To | Payload |
| --- | --- | --- |
| `LISTED_ON` | Company → Exchange | ticker, listing_date (optional) |
| `IN_INDUSTRY` | Company → Industry | scheme |
| `SUBSIDIARY_OF` | Company → Company | since |
| `OWNS_STAKE_IN` | Company → Company | percentage |

Rules: claims are **append-only and never destructively merged** — conflicting claims
coexist; which one "wins" is **read-time policy** (most-recent `as_of`, highest
verifiability, or "show all with sources"); cross-source **agreement upgrades confidence**,
divergence is itself a data-quality signal to surface — the same posture as the fact store's
multi-adapter rule (§2.1).

**Example: the ownership claims of the fictional seed.** Each edge shows its payload, its
source, and its `as_of`. Beta → Gamma has three stake claims: 75 % and 60 % for 2026-01-31 are a
conflict, and 75 % for 2025-12-31 is an earlier point of a time series.

```cypher
MATCH p = (:Company)-[:SUBSIDIARY_OF|OWNS_STAKE_IN]->(:Company)
RETURN p
```

![Ownership claims between the fictional companies](../docs/images/ownership-claims.svg)

To list only the conflicts, run `queries/conflicting_ownership_claims/query.cypher`. It returns
one row: Beta (`C-000002`) → Gamma (`C-000003`), `as_of` 2026-01-31, 2 different percentages.

**Data-quality checks per element** (anchoring the review ask "how do we check consistency
for each of these"):

| Element | Check |
| --- | --- |
| `Company` | has ≥ 1 `Identifier`; exactly one *primary* id; no orphan companies |
| `Identifier` | validates against its scheme (LEI check digit, CIK format); LEI: GLEIF status current (issued, not lapsed); belongs to one company (`check_identifier_one_company`) |
| `HAS_FILING` / `Filing` | filing exists verbatim in the adapter raw store (§8 drift check) |
| `FiscalYear` / `FiscalQuarter` | the quarters follow each other with no gap and no overlap and cover the year (`check_fiscal_quarters`) |
| `REPORTS_ON` | every filing reports on a fiscal period (`check_filing_has_period`) |
| `REPORTS_CONCEPT` | expected-concept set for the form type covered (completeness, §5.4) |
| ownership claims | `percentage ∈ (0, 100]`; `as_of ≤ observed_at`; conflict detector: same edge + same `as_of`, different payloads |
| every claim | its `source` is in the `Source` list (`check_source_known`) |

### 5.3 Diagram

```mermaid
graph LR
  subgraph Reference["Reference data (loaded first)"]
    S["Source (SEC / GLEIF / vendor)"]
    T["FormType"]
    K["Concept (CanonicalElement)"]
  end
  subgraph CoreAx["Ring 1 — axiomatic core (every company ever)"]
    C["Company (PK: our own id)"]
    ID["Identifier (LEI / CIK / …)"]
  end
  subgraph Adapter["One adapter per source"]
    G["Registrant (native id: CIK or LEI)"]
    Y["FiscalYear"]
    Q["FiscalQuarter"]
    F["Filing (native id: accession)"]
  end
  subgraph Claims["Claim layer (source-attributed)"]
    E["Exchange"]
    I["Industry (per scheme)"]
    C2["Company (related)"]
  end
  T -- REQUIRES --> K
  C -- HAS_IDENTIFIER --> ID
  C -- REGISTERED_WITH --> G
  G -- HAS_FILING --> F
  G -- HAS_FISCAL_YEAR --> Y
  Y -- HAS_QUARTER --> Q
  F -- REPORTS_ON --> Y
  F -- REPORTS_ON --> Q
  F -- REPORTS_CONCEPT --> K
  C -. "LISTED_ON {source, as_of}" .-> E
  C -. "IN_INDUSTRY {source, scheme}" .-> I
  C -. "SUBSIDIARY_OF {source, as_of}" .-> C2
  C -. "OWNS_STAKE_IN {source, as_of, %}" .-> C2
```

### 5.4 Two workloads under one "graph" label

The knowledge-graph *modeling* lens covers two very different **query shapes**, and conflating
them oversells the need for a graph *engine*. Separating them sharpens the storage decision
(§13–§14):

**(a) Structural completeness — relational-shaped (bounded, shallow).** Despite the "graph"
framing, these are set/aggregate operations, not traversals — a row store does them *better*
than a graph engine:

- _"Which companies are missing a Q3-2024 quarterly report?"_ → an **anti-join**.
- _"Does FY2024 have all four quarters?"_ → a **GROUP BY / count**.
- _"Which required concepts did this filing fail to report?"_ → a **set difference** between
  expected `Concept`s and the filing's `REPORTS_CONCEPT` edges.

  1-hop edges (`HAS_FILING`, `REPORTS_ON`, `REPORTS_CONCEPT`) are just indexed joins. This
  is the **completeness engine**, and it stays comfortable in Postgres at the stated scale.

**(b) Relationship traversal — genuinely graph-shaped (deep, variable-depth).** The
`SUBSIDIARY_OF` / `OWNS_STAKE_IN` edges form corporate ownership networks:

- _"Ultimate parent of company X"_, _"full beneficial-ownership tree"_, _"all cross-holdings
  between two groups"_ → **recursive, multi-hop** traversals.

  Here a native graph engine (index-free adjacency, Cypher) materially beats recursive CTEs,
  which grow verbose and degrade with depth/branching.

**Consequence for the decision:** completeness (a) does *not* justify a graph database;
relationship traversal (b) is the only workload that does. So the §14 trigger for adopting a
dedicated graph store is specifically *"when multi-hop ownership/relationship analysis becomes
central,"* not the data-quality checks.

### 5.5 The adapter layer (lab addition)

The core `Company` knows nothing about fiscal years or filings. It delegates to a source through
one edge, `REGISTERED_WITH`. Everything one source says about a company hangs below one
`Registrant`:

```text
Company (core, C-000007)
 ├─ REGISTERED_WITH → Registrant (SEC, CIK 0000320193)
 │    ├─ HAS_FILING → Filing
 │    └─ HAS_FISCAL_YEAR → FiscalYear
 │         ├─ REPORTS_ON ← Filing (10-K)
 │         └─ HAS_QUARTER → FiscalQuarter {calendar_quarter}
 │              └─ REPORTS_ON ← Filing (10-Q)
 └─ REGISTERED_WITH → Registrant (GLEIF, LEI HWUPKR0MPOU8FGXBT394)
```

**Example: Apple under the SEC.** The fiscal year runs from October to September. Each of the
first three quarters has its 10-Q, the year has its 10-K, and the fourth quarter has no filing
of its own.

```cypher
MATCH p = (:Company {name: 'Apple Inc.'})-[:REGISTERED_WITH]->
          (:Registrant {source: 'SEC'})-[:HAS_FISCAL_YEAR]->(:FiscalYear)
          -[:HAS_QUARTER]->(q:FiscalQuarter)
OPTIONAL MATCH f = (:Filing)-[:REPORTS_ON]->(q)
OPTIONAL MATCH k = (:Filing)-[:REPORTS_ON]->(:FiscalYear {registrant: '0000320193'})
RETURN p, f, k
```

![Apple, its SEC registrant, fiscal year 2024, the quarters, and the filings](../docs/images/sec-fiscal-tree.svg)

The text below each quarter gives its last day and its `calendar_quarter`. Apple's first fiscal
quarter of 2024 is the calendar quarter `Q4-2023`.

Four rules keep the adapters apart:

1. **One root per company and source.** The `Registrant` is the only door from the core into a
   source.
2. **The source starts every key.** A fiscal year is `(source, registrant, fiscal_year)`, a filing
   is `(source, native_id)`. Data of two sources never merges into one node.
3. **A subtree links only to itself, to the core, and to reference data.** Two sources meet
   through `calendar_quarter` and `Concept`, never directly.
4. **Each adapter node leads up to one root.** That root names the source.

Postgres enforces rules 2 to 4 with composite foreign keys. Neo4j has no foreign keys. A check
for these rules needs a planted violation, and Postgres rejects such a row, so the lab has no
such check.

- **A fiscal period is adapter data, not a shared dimension.** Apple's fiscal year 2024 runs from
  2023-10-01 to 2024-09-28. No arithmetic gives these dates: the filing declares them. So the
  node has a source, and `check_fiscal_quarters` tests it for consistency.
- **A fiscal year number is the filer's own label.** NVIDIA calls the year that ends in January
  2024 "fiscal 2024". Target gives that name to the year that ends in February 2025.
- **`calendar_quarter` compares companies.** It holds the calendar quarter of the middle day of
  a fiscal quarter, for example `Q3-2024`. Filter on it to compare companies with different
  fiscal years.
  This query returns the fiscal quarter of three companies that falls in `Q3-2024`:

  ```sql
  SELECT g.registered_name, q.quarter AS fiscal_quarter, q.start_date, q.end_date
  FROM fiscal_quarter q
  JOIN registrant g ON g.source = q.source AND g.native_id = q.registrant
  WHERE q.calendar_quarter = 'Q3-2024'
    AND g.registered_name IN ('Apple Inc.', 'VISA INC.', 'TARGET CORP');
  ```

  | registered_name | fiscal_quarter | start_date | end_date |
  | --- | --- | --- | --- |
  | Apple Inc. | 4 | 2024-06-30 | 2024-09-28 |
  | TARGET CORP | 3 | 2024-08-04 | 2024-11-02 |
  | VISA INC. | 4 | 2024-07-01 | 2024-09-30 |

  Microsoft and NVIDIA are absent from this result, although both were in the list at first:
  their fiscal 2024 ended before July 2024, and the seed holds one fiscal year per company.
- **A filing stays attributable.** It hangs on the period it reports on, so each period leads to
  its source in one hop. `HAS_FILING` holds every filing, also one whose period is unresolved.
- **The fourth quarter has no 10-Q.** Its node exists, and its numbers are the year minus the
  first three quarters.
- **A filing that declares the wrong period stays visible.** AES tagged its 10-Q for March 2024
  as the second quarter of fiscal 2022. The filing hangs on the registrant through `HAS_FILING`
  and reports on nothing, and the first quarter has no filing. `check_filing_has_period` and
  `incomplete_fy2024` both find it.

  ```cypher
  MATCH (c:Company {name: 'AES CORP'})-[:REGISTERED_WITH]->(g:Registrant {source: 'SEC'})
  MATCH p = (c)-[:REGISTERED_WITH]->(g)-[:HAS_FISCAL_YEAR]->()-[:HAS_QUARTER]->()
  OPTIONAL MATCH f = (g)-[:HAS_FILING]->(:Filing)
  OPTIONAL MATCH r = (g)-[:HAS_FILING]->(:Filing)-[:REPORTS_ON]->()
  RETURN p, f, r
  ```

  ![AES: one 10-Q hangs on the registrant only, and the first quarter has no filing](../docs/images/mislabelled-filing.svg)

  The figure leaves out the `HAS_FILING` edges of the filings that do report on a period.
- **A regulator gives filings and fiscal periods, so it gets a subtree.** A vendor or a news
  feed gives opinions about relationships, so it stays on claim edges. Both name a `Source`.
- **`Identifier (CIK)` and `Registrant` overlap on purpose.** The identifier is the identity
  record in the core. The registrant is the root of the adapter data.

### 5.6 Company identity (lab addition)

`company_id` is an id that we mint, such as `C-000007`. It carries no meaning and never changes.
Everything the world uses to point at a company is an `Identifier` on that company.

**Example: Apple.** One company node, two identifiers, and one registrant per source. The id
`C-000007` appears nowhere outside the lab.

```cypher
MATCH (:Identifier {scheme: 'LEI', value: 'HWUPKR0MPOU8FGXBT394'})<-[:HAS_IDENTIFIER]-(c:Company)
MATCH p = (c)-[:HAS_IDENTIFIER|REGISTERED_WITH]->()
RETURN p
```

![Apple with its CIK, its LEI, and its registrants at the SEC and at GLEIF](../docs/images/company-identity.svg)

The same lookup in Postgres, with what each source says about the company:

```sql
SELECT g.source, g.native_id, g.registered_name, g.since, g.jurisdiction, g.status
FROM has_identifier h
JOIN registrant g USING (company_id)
WHERE h.scheme = 'LEI' AND h.value = 'HWUPKR0MPOU8FGXBT394';
```

| source | native_id | registered_name | since | jurisdiction | status |
| --- | --- | --- | --- | --- | --- |
| SEC | 0000320193 | Apple Inc. | 1994-01-26 | | |
| GLEIF | HWUPKR0MPOU8FGXBT394 | Apple Inc. | 2012-06-06 | US-CA | ISSUED |

- **Find a company by a handle, never by the id.** `(scheme, value)` is unique, so a CIK or an
  LEI leads to one company in one hop. A ticker leads to it through `LISTED_ON`. A name gives a
  list of candidates, never one sure answer.
- **Two records are the same company if they share a strong identifier:** an LEI, a CIK, or a
  national register number. `check_identifier_one_company` finds an identifier on two companies.
- **Mint once, remember forever.** `fixtures/company_ids.json` records which identifiers lead
  to which id. A load asks this registry first and mints only for a company it does not know. So
  a company keeps its id when the stores are created again, and when it gets a new identifier.
- **A `Company` is one legal entity.** "The Apple" that people talk about is the top entity,
  Apple Inc. Its other entities hang below it through `SUBSIDIARY_OF`.
- **`primary` marks the preferred handle to show.** It no longer says where the key comes from.

Why not arkad's rule, the LEI as key with the CIK as fallback: EDGAR gives no LEI, so all 100
real companies start with a CIK key. 94 of them get an LEI from GLEIF, and each of those keys
must then change. 11 of the 94 LEIs have lapsed.

### 5.7 Node or property (lab addition)

Make something a node if it has relationships of its own, or if a query passes through it. Make
it a property if a query only filters by it.

A shared label as a node becomes a hub. The calendar quarter `Q3-2024` had 88 edges with 100
companies and one fiscal year. With all filers and ten years, it has tens of thousands. No query
passes through it, and it hides every picture.

| Was | Now | Why |
| --- | --- | --- |
| `Period` node, `ALIGNS_WITH` edge | `FiscalQuarter.calendar_quarter`, with an index | Only a filter. Calendar dates need no node |
| `Regulator` node with an edge from each registrant | `Source` node with no edges, `source` property in each key | Only a filter. The node stays as a list of names and kinds |
| `OF_FORM` edge | `Filing.form` property | Only a filter. `FormType` stays a node, because `REQUIRES` is real structure |
| `Concept` node | unchanged | The set difference "required minus reported" passes through it. It is the next hub to watch |
| `Exchange`, `Industry` nodes | unchanged | Queries pass through them: "who else is in this industry" |

In Postgres each of these was a column already. The parts of the model that are shared labels
are relational in shape. Only the company-to-company parts are graph-shaped (§5.4).

### 5.8 Assessment (lab addition)

An opinion on the model as it stands, from the work on 100 real companies. The numbers come
from the seed: 1,499 nodes and 3,875 edges in Neo4j.

**What works**

- **Core and adapters are separate.** GLEIF came in as a second source without one change to
  `Company`. This is the strongest evidence in the lab.
- **Fiscal periods as adapter data.** With calendar periods, `incomplete_fy2024` flagged 24 real
  companies. With fiscal periods it flags two, and both are real: a filing that declares the
  wrong period.
- **Our own company id.** No key changes when an identifier arrives. The six companies without
  an LEI are ordinary companies.
- **The node-or-property rule.** Each node has a reason to exist, so the next modelling
  question has a rule, not a taste.
- **Checks as queries.** Each rule is a question with planted violations, and both stores must
  give the same rows. A wrong query fails on at least one store.
- **One load path.** `scripts/load_stores.py` builds both stores from nothing, in a fixed order.

**What does not work yet**

- **`Concept` is a hub.** Five nodes hold 1,889 of the 3,875 edges: 49 % of the graph points at
  five nodes. `Assets` has 411 edges with one fiscal year. This is the calendar-quarter problem
  again, at a larger scale, and it gets worse with every fact.
- **The graph holds no fact.** It says that a filing reports `Revenue`, never the amount. The
  amounts are relational in shape and belong in Postgres.
- **Both stores hold everything.** The lab loads the same data into Neo4j and Postgres to
  compare them. That is right for a comparison and wrong as a design: no store has a
  responsibility of its own yet.
- **`Registrant` does two jobs.** For the SEC it is the root of a tree. For GLEIF it is a flat
  record with three properties that only GLEIF fills. A third source adds more of them.
- **The graph-shaped part runs on fiction.** `SUBSIDIARY_OF` and `OWNS_STAKE_IN` exist only
  between the six fictional companies. The one workload that justifies a graph engine (§5.4)
  has not met real data.
- **Identity resolution happens outside the model.** A script matches EDGAR to GLEIF by name and
  one more fact. It found 94 of 100, and only three of them are checked by hand. The model
  records the result, not how sure the match is.
- **One fiscal year, no amendments.** A changed fiscal year end, a restated figure, and a
  `10-K/A` are the cases that break period models. None of them is in the seed.
- **Postgres enforces what Neo4j cannot.** Composite foreign keys keep the adapters apart in
  Postgres. Neo4j accepts a filing under the wrong registrant without complaint.

**Where this points**

Each hub that became a property turned an edge into a column. What remains as true graph
structure is the ownership network, and a tree that a foreign key handles well. So the split
that the data suggests is:

| Store | Responsibility | Holds |
| --- | --- | --- |
| Graph | Who is it, and how is it related | `Company`, `Identifier`, `Registrant`, the claim layer |
| Postgres | What was reported, and when | Fiscal periods, filings, facts, time series, raw source records |

The stores share keys, not data: `company_id`, the registrant key `(source, native_id)`, and
the concept `element`. A question runs in one direction: the graph finds the set of companies,
and Postgres returns their numbers. Whether filings and fiscal periods belong on the graph side
or the Postgres side is the next decision. This table puts them in Postgres, because every
question about them so far was a filter or a join.
