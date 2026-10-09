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
| `Company` | **core — axiomatic** | `company_id` (§4) | *the* non-negotiable node; entity_name, country, status |
| `Identifier` | **core — axiomatic** | `(scheme, value)` e.g. `(LEI, …)`, `(CIK, …)` | identity records attached to `Company`; each verifiable against its issuing registry (GLEIF, EDGAR) |
| `Concept` | core — ours by construction | `CanonicalElement` | our own vocabulary — axiomatic because *we* define it (enables "which concepts expected/missing") |
| `Period` | shared dimension | `(kind, key)` e.g. `FY2024`, `Q3-2024` | deterministic calendar construct (Instant/Duration) — verifiable by arithmetic, safe to share |
| `Regulator`/`DataSource` | adapter-bridge | `code` (SEC, FCA, BaFin, ESMA) | |
| `Filing` | adapter | `regulator + native_id` (SEC: accession) | form, filed_date, period_end, taxonomy version |
| `Exchange` | reference data | `mic` (ISO 10383) | the *list* is a verifiable standard; any given *listing* is a claim (§5.2) |
| `Industry`/`Sector` | **claim layer — not core** | `scheme+code` (GICS/SIC/NACE) | classifications are source-owned opinions (GICS is S&P/MSCI's, SIC is the SEC's), multi-label, and disagree across schemes — attached only via source-attributed `IN_INDUSTRY` claims |

**Build order (review directive):** ring 1 (`Company` + `Identifier`) → the SEC adapter
(`Regulator`, `Filing` + structural edges) → the bridge (`HAS_FILING` via CIK→`CompanyId`
resolution, §11). Claim-layer nodes enter only as their sources are onboarded.

### 5.2 Edges — structural vs claims

**Structural edges** — adapter-verifiable (a filing either exists in EDGAR or it doesn't):

| Edge | From → To | Properties |
| --- | --- | --- |
| `HAS_IDENTIFIER` | Company → Identifier | since, status (active / lapsed) |
| `HAS_FILING` | Company → Filing | (Filing is adapter-owned but hangs off the core company) |
| `FILED_UNDER` | Filing → Regulator | |
| `FILES_WITH` | Company → Regulator | first_filed |
| `COVERS_PERIOD` | Filing → Period | |
| `REPORTS_CONCEPT` | Filing → Concept | resolved confidence (structural completeness) |

**Relationship edges — source-attributed claims.** A relationship assertion is only as good
as its source, and sources disagree: `A OWNS_STAKE_IN B: 42% as of 2026-01-31 per S1` can
coexist with `… 53% as of 2026-01-16 per S2` (different `as_of` — a legitimate time series,
not a conflict) *and* with `… 53% as of 2026-01-31 per S2` (same `as_of` — a genuine
conflict). So every relationship edge carries a uniform **claim envelope** beside its payload:

- `source` — which adapter/dataset asserted it (provenance, §8.2)
- `as_of` — the date the assertion is *about*; `observed_at` — when we ingested it
- `verifiability` — `Verified` (regulatory filing / official registry) · `Reported`
  (reputable aggregator or data vendor) · `Alleged` (news, unconfirmed)

| Edge (claim) | From → To | Payload |
| --- | --- | --- |
| `LISTED_ON` | Company → Exchange | ticker, listing_date |
| `IN_INDUSTRY` | Company → Industry | scheme |
| `SUBSIDIARY_OF` | Company → Company | since |
| `OWNS_STAKE_IN` | Company → Company | percentage |

Rules: claims are **append-only and never destructively merged** — conflicting claims
coexist; which one "wins" is **read-time policy** (most-recent `as_of`, highest
verifiability, or "show all with sources"); cross-source **agreement upgrades confidence**,
divergence is itself a data-quality signal to surface — the same posture as the fact store's
multi-adapter rule (§2.1).

**Data-quality checks per element** (anchoring the review ask "how do we check consistency
for each of these"):

| Element | Check |
| --- | --- |
| `Company` | has ≥ 1 `Identifier`; exactly one *primary* id; no orphan companies |
| `Identifier` | validates against its scheme (LEI check digit, CIK format); LEI: GLEIF status current (issued, not lapsed) |
| `HAS_FILING` / `Filing` | filing exists verbatim in the adapter raw store (§8 drift check) |
| `COVERS_PERIOD` | period arithmetic consistent (dates ↔ fiscal year; four quarters ≈ FY, §5.4) |
| `REPORTS_CONCEPT` | expected-concept set for the form type covered (completeness, §5.4) |
| ownership claims | `percentage ∈ (0, 100]`; `as_of ≤ observed_at`; conflict detector: same edge + same `as_of`, different payloads |

### 5.3 Diagram

```mermaid
graph LR
  subgraph CoreAx["Ring 1 — axiomatic core (every company ever)"]
    C["Company (PK: CompanyId)"]
    ID["Identifier (LEI / CIK / …)"]
  end
  subgraph Adapter["SEC adapter (+ shared dimensions)"]
    R["Regulator (SEC/FCA/…)"]
    F["Filing (native id: accession)"]
    K["Concept (CanonicalElement)"]
    P["Period"]
  end
  subgraph Claims["Claim layer (source-attributed)"]
    E["Exchange"]
    I["Industry (per scheme)"]
    C2["Company (related)"]
  end
  C -- HAS_IDENTIFIER --> ID
  C -- HAS_FILING --> F
  C -- FILES_WITH --> R
  F -- FILED_UNDER --> R
  F -- COVERS_PERIOD --> P
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

  1-hop edges (`HAS_FILING`, `COVERS_PERIOD`, `REPORTS_CONCEPT`) are just indexed joins. This
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
