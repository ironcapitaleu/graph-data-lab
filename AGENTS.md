# Lab Rules

This repo is a sandbox for the arkad knowledge-graph data model (`ironcapitaleu/arkad`). It tests
the model on Neo4j and Postgres side by side. `README.md` explains the layout and how to run it.

## Workflow

- Commit straight to `main`. This repo uses no pull requests.
- Run `uv run pytest` before every push. All tests must pass.
- Never change arkad from this repo. A useful result reaches arkad only through a separate arkad PR.

## Model Rules

- `model/MODEL.md` is the lab's own copy of the model. Change it freely. It does not need to match
  arkad.
- A model change touches every layer in one commit: `MODEL.md`, both schemas, both seeds,
  `fixtures/README.md`, and the affected queries.
- If you add something that arkad's model does not have, note it at the top of `MODEL.md`.
- Data-quality rules are queries in `queries/check_*`, not database constraints. The seed holds
  planted violations for them.

## Test Rules

Load the `lab-testing` skill for any change to `queries/`, `fixtures/`, or `tests/`. The core:

- Each question has a Cypher query, a SQL query, and one shared `expected.json`.
- Write `expected.json` from the seed by hand, never from a query result.
- Every new test failed once on purpose before you trust it.

## Writing Style

Load the `plain-english` skill before you write prose of any length. The core: short sentences,
active voice, `can`/`will`/`must` instead of `should`/`may`, one word per concept, no filler.

## Commit Messages

Format: `<type>[(<scope>)]: <short summary>`, imperative mood, under 72 characters. The body says
why, not what.

Types: `feat` (new question, model change), `fix`, `refactor`, `test`, `doc`, `build`
(dependencies, Docker), `chore`.

## Reporting

Report to the user in short, plain sentences. Give the test result and anything worth porting
back to arkad.
