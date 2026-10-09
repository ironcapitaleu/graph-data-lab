---
name: handoff
description: >
  Use when the user asks to "hand off", "create a handoff", "start a new session for this", or
  invokes `/handoff`. Compacts the current conversation into a self-contained prompt for a fresh
  agent session in this lab.
version: 0.1.0
---

# Handoff Skill

## Purpose

Compact the current conversation into a standalone prompt. A fresh session reads only that prompt,
so it must carry every fact the next session needs.

Adapted from the arkad `handoff` skill. The Linear destination is removed, because the lab does
not track work in Linear.

## Procedure

1. **Read the argument.** If the user gave no focus, ask once what the next session will do.
2. **Compile the document** with the template below. Reference files by path and commits by hash.
   Do not paste file contents that the next session can read itself.
3. **Redact secrets.** Name where a secret lives, never its value. The default passwords in
   `docker-compose.yml` are local test values, so you can name the file.
4. **Deliver.** Write the document to a temporary directory outside the repository, as
   `handoff-<short-slug>.md`. Never commit it. Show it to the user in one fenced code block, so they
   can copy it in one click.

## Template

```markdown
# Mission

<One or two sentences. The exact outcome the next session must reach.>

# Context

<What the lab is, its link to arkad, and where the work stands now.>

# Current State

- Done: <commits on main, by hash>
- In flight: <uncommitted work, open questions>
- Blocked / undecided: <what waits on the user, and what unblocks it>

# Key Decisions

<One line each. Link the file that records the decision.>

# Artifacts

<Files, commits, and arkad documents, by path or URL.>

# Suggested Skills

<The skills in .claude/skills/ the next session must load, and when.>

# Next Steps

1. <Ordered, concrete first action.>

# Guardrails

<Each as `must` or `never`.>

# Reporting

<When and how to report to the user.>
```

## Critical Invariants

- **Self-contained.** If a fact is not in the prompt, the next session does not have it.
- **Reference, do not duplicate.** Link files and commits. Never copy their bodies.
- **Never in the repository.** The handoff file goes to a temporary directory.
- **Plain English.** The `plain-english` skill applies.
