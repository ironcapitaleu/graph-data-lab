# graph-data-lab

A sandbox to test arkad's knowledge-graph data model on a real graph database and on Postgres.

The model started as a copy of arkad `sec/design/data_model/hybrid_data_model.md` §5. This repo
owns its copy and changes it freely. If a result is useful, port it back to arkad in a normal PR.

## What it tests

Each question from the arkad design runs as a query against both stores. Both results must equal
the same expected rows:

| Query | Question | Shape |
| --- | --- | --- |
| `missing_q3_2024` | Which SEC filers have no Q3-2024 report? | anti-join |
| `incomplete_fy2024` | Which SEC filers miss any FY2024 report? | anti-join |
| `filing_missing_concepts` | Which required concepts did a filing not report? | set difference |
| `ultimate_parent` | What is the top parent of each subsidiary? | multi-hop traversal |
| `ownership_tree` | Which companies sit below Alpha, and how deep? | multi-hop traversal |
| `conflicting_ownership_claims` | Which ownership claims disagree on the same date? | group by |
| `check_*` | The data-quality checks from §5.2 | filters |

## Layout

```text
model/
  MODEL.md          working copy of the graph model (nodes, edges, checks)
  schema.cypher     the model in Neo4j
  schema.sql        the same model as Postgres tables
fixtures/
  README.md         the seed companies and the planted gaps and violations
  seed.cypher       seed data for Neo4j
  seed.sql          the same seed data for Postgres
queries/<name>/
  query.cypher      the question in Cypher
  query.sql         the question in SQL
  expected.json     the rows both queries must return
tests/
  conftest.py       resets both stores, then loads the schema and the seed
  repo_files.py     paths to the files above and a reader for them
  test_queries.py   runs every query on both stores
  test_parity.py    checks that both seeds hold the same data
pyproject.toml      dependencies and pytest settings, managed by uv
ruff.toml           format and lint settings
AGENTS.md           rules for agents working in the lab
DOCUMENTATION.md    rules for Python docstrings
.claude/skills/     agent skills: lab-testing, performance, plain-english,
                    xbrl-accounting, handoff
```

## Run it

You need Docker and [uv](https://docs.astral.sh/uv/). uv installs the Python version from
`.python-version` if you lack it.

```sh
docker compose up -d --wait
uv run pytest
```

`uv run` creates `.venv` and installs the locked dependencies from `uv.lock` on first use. To add
a dependency, run `uv add <package>` (or `uv add --dev <package>`) and commit `pyproject.toml` and
`uv.lock`.

Before you push, run the checks from the "Pre-Push Checks" section of `AGENTS.md`: format, lint,
type checks, tests, and the vulnerability audit.

The tests wipe both databases, then load the schema and the seed. Do not point them at a database
you want to keep.

To look at the graph, open the Neo4j Browser at <http://localhost:7474>. Log in as `neo4j` with
password `graph-data-lab`, then run `MATCH (n) RETURN n`.

Connection settings come from `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` and `POSTGRES_DSN`. The
defaults match `docker-compose.yml`.

## Add a question

1. Create `queries/<name>/`.
2. Write `query.cypher` and `query.sql`. Both must return the same column names.
3. Write `expected.json` as a list of rows. Row order does not matter.
4. If the question needs new data, add it to both seed files and list it in `fixtures/README.md`.

## Not covered yet

- LEI check digits (ISO 17442) and GLEIF status for the identifier check.
- The `REPORTS_CONCEPT` drift check against the adapter raw store.
- Period arithmetic: a filing's `period_end` against its period's dates.
- Performance. The seed has 6 companies, so the timings mean nothing yet.
