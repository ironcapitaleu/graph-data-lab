# Documentation Guidelines

This document defines the standards for Python documentation in this project. It states **what** to
document, **how** to structure a docstring, and **where** to place a doc example.

The document has three parts:

1. **General Principles** — the W-Fragen framework and the list of documentable items
2. **Per-Item Sections** — modules, functions, classes, enums, protocols, constants, errors
3. **Cross-Cutting Reference** — coupling rules, references, doc examples, enforcement, checklist

The lab holds Python only under `tests/` today. The rules for libraries apply when the lab gets a
package under `src/`, such as a seed generator. The examples use a placeholder package named
`my_package`.

---

## General Principles

- Every public item in a library package **must** have a docstring.
- A docstring describes the **contract**: what the item does, what it guarantees, and its limits. It
  does not describe the implementation.
- Write for a reader who knows Python and does not know this codebase.
- Keep the first line short and self-contained. Editors and `help()` show it as the preview.
- Use present tense, third person: "Returns the validated CIK", not "This will return..." or
  "Return the CIK".
- Choose `a` or `an` by the **spoken sound**, not the first letter. "HTTP" starts with the sound
  "aitch", so write "an HTTP response".
- Prefer clarity over terseness. A few extra words that remove an ambiguity beat a shorter phrase
  that reads as jargon.
- When you tighten a docstring that is already good, **blend**. Keep the established opening and
  add to it. Do not rewrite it from zero.
- The [`plain-english` skill](.claude/skills/plain-english/SKILL.md) decides the wording. This
  document decides the structure.

### Documentable Items

| Item kind | Example | Where the documentation goes |
| --------- | ------- | ---------------------------- |
| Package | `my_package/domain/__init__.py` | Docstring at the top of `__init__.py` |
| Module | `cik.py` | Docstring at the top of the file |
| Function / Method | `def validate() -> None:` | Docstring below the signature |
| Class | `class Cik:` | Docstring below the `class` line, with `Args:` and `Attributes:` |
| Dataclass field | `value: str` | `Attributes:` section of the class docstring |
| Enum | `class StatusCode(Enum):` | Class docstring, with one `Attributes:` entry per member |
| Protocol / abstract base class | `class SecResponse(Protocol):` | Class docstring and one docstring per method |
| Constant | `CIK_LENGTH: Final = 10` | String literal on the line below the assignment |
| Type alias | `type Headers = Mapping[str, str]` | String literal on the line below the assignment |
| Re-export | `from my_package.cik import Cik` | Not required. The target item carries the docstring. |

### The W-Fragen Principle

Every docstring answers a subset of these questions, in this priority order:

| Question | Answers | Applicable items | Required? |
| -------- | ------- | ---------------- | --------- |
| **Was?** (What?) | What does this item do or represent? | All | Always. This is the summary line. |
| **Warum?** (Why?) | Why does it exist? Which problem does it solve? | Modules, classes, protocols, enums, type aliases | When the "what" alone does not justify the item |
| **Wie?** (How?) | How does it achieve its purpose? | Modules, functions, protocols | When the signature does not show the mechanism |
| **Wer?** (Who?) | Who implements this? | Protocols, abstract base classes | For extension points |
| **Wann?** (When?) | Under which condition does this occur? | Enum members, errors, callbacks | For error cases and callbacks |
| **Wo?** (Where?) | Where does this value originate? | Modules, classes, constants | When the origin is not obvious |

Not every item needs every answer. An accessor needs only *Was?*. A protocol can need all six. A
reader must never have to guess the answer to a question they naturally ask.

### Docstring Syntax

- Use triple double quotes (`"""`). Never use single quotes or a `#` comment block as a docstring.
- Follow **Google style**. Ruff enforces it (rule `D`, `convention = "google"`).
- Put the summary on the same line as the opening quotes. End it with a period.
- Leave one blank line between the summary and the rest.
- Use these sections, in this order: `Args:`, `Attributes:`, `Returns:`, `Yields:`, `Raises:`,
  `Examples:`.
- Never repeat a type in a docstring. The annotation is the source of truth.
- Wrap a code name in single backticks: `` `validated_cik` ``.

---

## Modules and Packages

Every package `__init__.py` and every module **must** have a docstring.

### Module Categories

| Category | Purpose | Example |
| -------- | ------- | ------- |
| **Grouping package** | Organizes related child modules under one namespace | `shared/__init__.py` groups `cik`, `http_client`, `response` |
| **Single-type module** | Holds one primary class with its supporting code | `fiscal_year.py` holds `FiscalYear` |

- A **grouping package** needs the full structure: what-sentence, why/how paragraph, `Modules:` list.
- A **single-type module** needs only the what-sentence. The class inside carries the detail.

### Content Structure

1. **What-sentence** — one sentence that answers "What does this module provide?". This is the
   summary line.
2. **Why/How paragraph** — after a blank line, two or three sentences. They answer "Why does this
   module exist?" and "How does it achieve its purpose?". A single-type module can omit it.
3. **`Modules:`** — a list of the child modules, each with a one-line description. Grouping packages
   only.
4. **`Examples:`** *(optional)* — a doc example that composes several items of the module.

### What Does Not Belong

A module docstring states **what the module provides** and **why it exists**. It leaves out team
**policy, process, and history**: where fixtures live, when to extract a shared package, why a past
decision was made. *Why this exists* helps the reader use the module. *Why we chose it* records a
debate the reader did not attend, and belongs in a design document or a skill.

**Avoid** — a policy essay in the module docstring:

```python
"""Common test fixtures.

Per the house convention, fakes live in `tests/fixtures/` and are not exported. A second
consumer that needs the same fake is the trigger to promote it to a shared package.
"""
```

**Prefer** — what the module provides and why, then its contents:

```python
"""Test fixtures that replace external systems.

The fixtures keep the unit tests independent of third-party services, I/O, and external state.

Modules:
    fake_write_repository: A fake `WriteRepository` that records what it persists.
"""
```

### Example

```python
"""Central Index Key (CIK) types.

Provides the `Cik` class, which parses and validates SEC Central Index Keys.

The SEC identifies every filer by a numeric CIK of exactly 10 digits, padded with zeros. This
package holds that invariant, so other code can rely on a `Cik` value without a second check.

Modules:
    cik_error: Errors for an invalid CIK.
    constants: Format constants such as `CIK_LENGTH`.
"""
```

---

## Functions and Methods

### W-Fragen

- **Was?** — Always. Start with a verb in third person present tense: "Creates", "Returns",
  "Validates".
- **Warum?/Wie?** — When the signature does not show the purpose or the mechanism.
- **Wann?** — For callbacks and for methods that run only under a condition.

### Content Structure

1. **What-sentence** (required) — at most about 80 characters. It is a complete sentence.
2. **Why/How paragraph** (when needed) — after a blank line.
3. **Sections** (when applicable, in this order):

| Section | When to include |
| ------- | --------------- |
| `Args:` | A parameter stays ambiguous even with a clear name and type |
| `Returns:` | The return value needs more than its type says |
| `Yields:` | The function is a generator |
| `Raises:` | The function raises an exception a caller can receive. List each one and its condition. |
| `Examples:` | Primary entry points and classes that validate or transform input |

Prefer a **self-documenting signature** over `Args:` and `Returns:`. Rename a parameter so that its
name and type carry the meaning: `domain_error: CikError`, not a bare `err`. The summary line is
then enough. If a signature cannot be made clear, add the sections.

### Conversions

A conversion function gets a **one-line summary that names the source and the target**:
"Converts a `CikError` into an `InvalidCikFormat` error."

### Examples

Minimal (accessor — what-sentence only):

```python
@property
def value(self) -> str:
    """Returns the validated CIK."""
    return self._value
```

Full (what, why/how, sections, doc example):

```python
def parse_cik(raw_cik: str) -> Cik:
    """Parses a raw string into a `Cik`.

    Removes surrounding whitespace and pads the value with zeros to 10 digits, so other code
    can rely on one format.

    Raises:
        InvalidCikFormat: The input contains a character that is not a digit, or it has more
            than 10 digits.

    Examples:
        >>> from my_package.domain.cik import parse_cik
        >>> parse_cik("123456789").value
        '0123456789'
    """
```

---

## Classes

### W-Fragen

- **Was?** — What does this type represent?
- **Warum?** — Why does it exist as its own type? This matters most for a wrapper around one value.
- **Wie?** — How does a caller construct it?

### Content Structure

1. **What-sentence** on the class.
2. **Why/How paragraph** when the what-sentence is not enough.
3. **`Args:`** — the constructor parameters that need an explanation. The class docstring documents
   the constructor. `__init__` gets no docstring of its own.
4. **`Attributes:`** — every public attribute, with "What does this hold?" and, when useful, "Where
   does it come from?".
5. **`Raises:`** — the exceptions the constructor raises.
6. **`Examples:`** — when construction validates or transforms the input.

When a class exists to give a value a stable string form, **document the exact output shape**:

```python
"""Formats as `["Revenue", "Total Assets"]`: brackets, quoted items, separated by commas."""
```

### Example

```python
@dataclass(frozen=True)
class PrepareSecRequestInput:
    """Input data for the preparation of an SEC request.

    Attributes:
        validated_cik: The CIK that the request targets.
        sec_client: The HTTP client that sends the request.
    """

    validated_cik: Cik
    sec_client: SecClient
```

---

## Enums

- **Was?** — Which family of values does this enum represent?
- **Warum?** — Why are these values one group?
- **Wann?** — For each member: under which condition does it occur?

List each member in the `Attributes:` section. Do not place a doc example on the enum itself. If an
example helps, place it on a method of the enum.

```python
class InvalidCikReason(Enum):
    """Enum representing the reason why a CIK failed format validation.

    Attributes:
        MAX_LENGTH_EXCEEDED: The CIK has more digits than the maximum allows.
        CONTAINS_NON_NUMERIC_CHARACTERS: The CIK contains a character that is not a digit.
    """

    MAX_LENGTH_EXCEEDED = "max_length_exceeded"
    CONTAINS_NON_NUMERIC_CHARACTERS = "contains_non_numeric_characters"
```

---

## Protocols and Abstract Base Classes

A `typing.Protocol` or an abstract base class defines a contract for several implementations. Its
docstring answers more questions than a concrete class.

- **Was?** — Which responsibility does this contract represent?
- **Warum?** — Why is this a contract and not a concrete class? Name the reason: several
  implementations, a fake in unit tests, or isolation from a third-party library.
- **Wie?** — How does an implementation fulfil the contract? State the invariants and any order
  constraint.

Rules:

- Document the contract on the class. Document each method on the method, with its own `Raises:`.
- Place a doc example on a method, never on the protocol class.
- If a method has a default implementation, state whether an implementation must override it, and
  under which condition.
- A generic contract stays free of domain vocabulary. See "External System vs. Internal Dependent".

```python
class SecResponse(Protocol):
    """Defines the interface of an HTTP response from the SEC API.

    Exists as a protocol to separate the library from any specific HTTP client. A unit test can
    then supply response data without a network call.
    """

    def body(self) -> Mapping[str, JsonValue]:
        """Returns the response body as a parsed JSON object."""
        ...
```

---

## Constants and Type Aliases

Place a string literal on the line below the assignment. A what-sentence is enough for most
constants. Add a why/how sentence only when the purpose of the value is not obvious. No doc example
is required.

```python
STATE_NAME: Final = "Validate CIK Format"
"""Human-readable name of the "Validate CIK Format" state, for error messages and log entries."""

type Headers = Mapping[str, str]
"""HTTP header names mapped to their values."""
```

---

## Error Documentation

### Wording

- Open the docstring of an error class with **"Error representing ..."** or **"Error indicating
  ..."**: "Error representing a CIK validation failure."
- Open the docstring of an error reason enum with **"Enum representing the reason why ..."**.
- Use **"error"** for the type. Use **"failure"** for the event the error represents. Never swap
  the two.
- Open with what failed: "Error occurring at the storage backend." Never open with the position of
  the error in a hierarchy.

### `Raises:` Section on Functions

A function that raises lists each exception a caller can receive, with its condition. The entry
answers "When can this fail, and with what?".

```python
"""
Raises:
    InvalidCikFormat: The input contains a character that is not a digit.
    FailedSecRequest: The SEC API returned a status code outside the 2xx range.
"""
```

Do not list an exception that signals a programming mistake of the caller, such as a `TypeError`
for a wrong argument type. The annotations cover those.

---

## What Not to Document

- **Private items** (a leading underscore) — document one only if its logic is subtle.
- **Obvious accessors** — a one-line summary is enough. Omit `Args:`, `Returns:`, and `Examples:`.
- **Magic methods** — `__init__`, `__str__`, `__eq__`, `__hash__`, and `__repr__` need no docstring.
  Document one only if its behavior deviates from what a reader expects.
- **Overrides** — a method that implements a protocol or overrides a base method inherits the
  contract. Mark it with `@override`. Document it only if its behavior deviates from the contract.
- **Tests** — a test function needs no docstring. Its name states the property. An integration
  test file needs a module docstring that lists its external dependencies. See the
  [`lab-testing` skill](.claude/skills/lab-testing/SKILL.md).

---

## Cross-Cutting Reference

### Describe the Item, Not Its Relationships

This is the rule that most reviews enforce. A docstring states what the item **is** and what it
**does**. It does not describe the item by its callers, its position, its history, or its use.

**Reference direction.** A docstring refers toward its **dependencies**, never toward its
**dependents**. The direction is the same as that of an `import` statement.

| Direction | Allowed? | Example |
| --------- | -------- | ------- |
| **Downward** (toward your dependencies) | Yes | `ValidateCikFormat` names `ValidateCikFormatInput` |
| **Sideways** (toward a sibling in the same module) | Yes | `PrepareSecRequestInput` names `SecClient` |
| **Upward** (toward code that depends on you) | No | `Cik` names a step that uses `Cik` |

One exception: the `Modules:` list of a package docstring describes the children of that package,
and a parent can state the order of its own children.

**Banned framings, with the fix:**

| Kind | Prose to avoid | Problem | Instead |
| ---- | -------------- | ------- | ------- |
| Caller | "passed in by the pipeline runner" | Names an internal dependent | State what the value is |
| Ordinal | "the second step of the extract phase" | A child claims its own position | Say what the step does |
| Temporal | "the first, minimal slice", "for now", "added later" | Describes a timeline, not a contract | "holds the persistence ports only" |
| Temporal | A ticket ID or a PR number | The code does not record the schedule | Delete it |
| Positional | "the innermost leaf of the error hierarchy" | Describes a position | "Error occurring at the storage backend." |
| Consumption | "shared across every operation class" | Describes the use, not the meaning | State what the error means |

State a deliberate limit as a **timeless property** ("names no concrete backend"). Never state it as
a deferral ("backends arrive in a later slice").

**Exception — when the relationship is the item.** A wrapper, a decorator, an adapter, or a
coordinator is defined by what it wraps, adapts, or combines. There, naming the relationship *is*
saying what the item does. The rule bans a relationship used as a *substitute* for meaning.

### External System vs. Internal Dependent

A reference to the *external system the package serves* is domain justification, and it belongs in
the docstring. A reference to an *internal dependent* is coupling. The test: does the reference
point at a real-world constraint the code exists to satisfy, or at another piece of *our* code that
uses it?

| Reference | Kind | Verdict |
| --------- | ---- | ------- |
| "under the SEC's limit of 10 requests per second" (on a rate limiter) | External system | Allowed. It explains why the value exists. |
| "paces outgoing SEC requests" (on a generic `RateLimiter` protocol) | Domain vocabulary in a generic contract | Avoid. The protocol paces callers, not "requests". |
| "shared across concurrently running pipelines" | Internal dependent | Avoid. Say "across all copies". |

A **generic protocol** stays free of domain vocabulary. The **module docstring, the constants, and
the concrete implementation** of the concept can name the external system.

### Do Not Restate the Code

- Never repeat the signature in prose. "Takes a string and returns a `Cik`" adds nothing.
- Never narrate a decorator or a keyword the reader can see, such as `@dataclass(frozen=True)`.
- Never use a jargon word in place of the meaning. Name what the value means.

### References to Other Items

Python docstrings have no checked links. Follow these rules:

- Name another item in single backticks: `` `Cik` ``, `` `Cik.value` ``, `` `InvalidCikReason.MAX_LENGTH_EXCEEDED` ``.
- Use the fully qualified name (`` `my_package.domain.cik.Cik` ``) only when the short name is ambiguous.
- Never use Sphinx roles such as `` :class:`Cik` ``.
- Name an item only when the reader needs it to understand the current one. Do not name a standard
  library type such as `str` or `Mapping` for this purpose.
- When you rename an item, search the docstrings for the old name. No tool reports a stale name.

### Doc Examples

A doc example answers *Wie?* with code. Pytest runs every example (`--doctest-modules`), so an
example is a test.

- **Required** on primary API entry points.
- **Required** on a class or function that validates or transforms its input.
- **Required** on a function whose error conditions are not obvious.
- **Optional** on an accessor. Prefer no example over an example that shows nothing.
- Place the example on the function or class it demonstrates. Use a module-level example only when
  several items must be composed to show the purpose of the module.

Mechanics:

- Write the example in `>>>` form under `Examples:`.
- Write each import as an external consumer writes it, from the package root.
- One example shows one behavior. End it with one expression and its output.
- If construction is the whole point and no output is meaningful, assign the result and show no
  output: `>>> digest = BodyDigest.from_bytes(b"...")`.
- If an example needs the network or another external system, add `# doctest: +SKIP` to the line
  that calls it.
- To show a raised exception, use the traceback form:

```python
"""
Examples:
    >>> parse_cik("12AB")
    Traceback (most recent call last):
        ...
    my_package.errors.InvalidCikFormat: [InvalidCikFormat] CIK must contain digits only
"""
```

### Enforcement

This command must pass:

```sh
uv run ruff check .
```

If the lab has a package under `src/`, this command must pass too:

```sh
uv run pytest --doctest-modules src
```

Ruff checks that a docstring exists and that its sections are well-formed. Ruff does not check the
wording, the coupling rules, or the content of `Raises:`. Check those by hand against this
document.

---

## Checklist for New Code

Before you push, verify:

- [ ] Every public item has a docstring with a summary line.
- [ ] Every module and every package `__init__.py` has a docstring.
- [ ] Every function that raises has a `Raises:` section.
- [ ] Every public attribute and every enum member has an `Attributes:` entry.
- [ ] Doc examples exist on entry points and on code that validates or transforms input.
- [ ] If `src/` exists, `uv run pytest --doctest-modules src` passes.
- [ ] Each docstring answers the relevant W-Fragen, at minimum *Was?*.
- [ ] No docstring names a caller, a position, a timeline, or a ticket ID.
- [ ] No docstring repeats a type or restates the code.
