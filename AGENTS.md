# Lab Rules

This repo is a sandbox for the arkad knowledge-graph data model (`ironcapitaleu/arkad`). It tests
the model on Neo4j and Postgres side by side. `README.md` explains the layout and how to run it.

## Workflow

- Commit straight to `main`. This repo uses no pull requests and no branches.
- Run the pre-push checks before every push. All of them must pass.
- Never change arkad from this repo. A useful result reaches arkad only through a separate arkad PR.
- If a change applies to several places, apply it everywhere in the same commit. Search the whole
  repo before you call the change complete.

## Tooling

One tool owns each job. Do not add a second tool for a job in this table.

| Job | Tool | Config |
| --- | ---- | ------ |
| Packages, virtual environment, lockfile | `uv` | `pyproject.toml`, `uv.lock` |
| Python versions | `uv python` | `.python-version` |
| Formatting | `ruff format` | `ruff.toml` |
| Linting, import order, docstring structure | `ruff check` | `ruff.toml` |
| Static type checks | `ty` | `pyproject.toml` (`[tool.ty]`) |
| Tests | `pytest` | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Vulnerability audit | `pip-audit` | — |
| Neo4j and Postgres | `docker compose` | `docker-compose.yml` |

- Run every Python command through `uv run`. Never call `python`, `pip`, `pytest`, `ruff`, or `ty`
  directly.
- Add a dependency with `uv add <package>`. Add a development dependency with
  `uv add --dev <package>`. Never edit the dependency lists in `pyproject.toml` by hand.
- Change the Python version with `uv python pin <version>`. Never use `pyenv`, `conda`, or a system
  Python.
- Never use `pip`, `poetry`, `pipenv`, `black`, `isort`, `flake8`, or `mypy`.
- Commit `uv.lock` and `.python-version`. Never commit `.venv/`.
- `ruff.toml` is the only place for Ruff settings. Never add a `[tool.ruff]` table to
  `pyproject.toml`.

## Pre-Push Checks

Start the stores with `docker compose up -d --wait`. Then run:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
uv run pip-audit
```

If a command fails, fix the cause before you push. To apply the automatic fixes, run
`uv run ruff format .` and `uv run ruff check --fix .`.

## Model Rules

- `model/MODEL.md` is the lab's own copy of the model. Change it freely. It does not need to match
  arkad.
- A model change touches every layer in one commit: `MODEL.md`, both schemas, both seeds,
  `fixtures/README.md`, and the affected queries.
- Never edit `fixtures/sp500.cypher` or `fixtures/sp500.sql` by hand. Change
  `scripts/generate_sp500_seed.py` and run it again.
- Never change or reuse an id in `fixtures/company_ids.json`. A company keeps its id for good.
- Keep the load order: reference data, the core, the adapters, the claims. `LOAD_ORDER` in
  `scripts/load_stores.py` fixes the order of the files.
- Make something a node if a query passes through it. Make it a property if a query only
  filters by it. See `MODEL.md` §5.7.
- If you add something that arkad's model does not have, note it at the top of `MODEL.md`.
- Data-quality rules are queries in `queries/check_*`, not database constraints. The seed holds
  planted violations for them.

## Test Rules

Load the `lab-testing` skill for any change to `queries/`, `fixtures/`, or `tests/`. The core:

- Each question has a Cypher query, a SQL query, and one shared `expected.json`.
- Write `expected.json` from the seed by hand, never from a query result. For the S&P 500 seed,
  `scripts/generate_sp500_seed.py` derives the rows from the EDGAR files.
- Every new test failed once on purpose before you trust it.
- Every test needs both stores, so all tests sit flat in `tests/`. Each test file has a module
  docstring that lists its external dependencies.
- Follow the "Arrange, Define, Act, Assert" pattern. Define the expected value as
  `expected_result` and capture the outcome as `result`. End with
  `assert result == expected_result`.
  Separate the four parts with one blank line. Never write label comments such as `# Arrange`.
- Write exactly one assertion per test function.
- Name a test `test_should_<behavior>_when_<condition>` or `test_should_<behavior>_for_<subject>`.
- Use `pytest.mark.parametrize` when the same assertion runs over several inputs.
- Use `pytest`. Never use `unittest.TestCase`.

## Python Rules

- Every function, method, and class attribute must carry type annotations. This includes tests.
- Never silence a check without a reason. A `# noqa: <rule>` or `# ty: ignore[<rule>]` comment
  must name the rule and state why on the same line.
- Use absolute imports. Never use wildcard imports. Put every import at the top of the file.
- Ruff orders the imports: standard library, third-party, first-party. Never sort them by hand.
- Write docstrings in Google style. [`DOCUMENTATION.md`](DOCUMENTATION.md) holds the rules for
  their structure. Ruff enforces their presence (rule `D`).
- If you must deviate from a rule, add a code comment that states why.

## Writing Style

Load the `plain-english` skill before you write prose of any length. The core: short sentences,
active voice, `can`/`will`/`must` instead of `should`/`may`, one word per concept, no filler.

## Commit Messages

Format: `<type>[(<scope>)]: <short summary>`, imperative mood, under 72 characters. The body says
why, not what.

Types: `feat` (new question, model change), `fix`, `refactor`, `style` (formatting only), `perf`,
`test`, `doc`, `build` (dependencies, Docker), `revert`, `chore`.

## Skills

A skill holds knowledge for one kind of work and loads only when that work starts. Skills live in
`.claude/skills/<name>/SKILL.md`.

- Put a rule that applies to all work in this file. Put domain procedures in a skill.
- A `SKILL.md` needs frontmatter with `name`, `description`, and `version`. The body holds
  `Purpose`, `Procedures`, and `Critical Invariants`.
- Put large lookup data in `.claude/skills/<name>/references/`, with a `last-verified` header.
- Keep external reference data in its original form. Never summarize it.

## Reporting

Report to the user in short, plain sentences. Give the test result and anything worth porting
back to arkad.
