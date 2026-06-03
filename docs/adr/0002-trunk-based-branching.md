# 0002. Trunk-based branching

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

`docs/BRANCHING.md` originally described a per-feature **integration branch**
(`NNN-short-name`): slices cut off it, merged up to it, then it merged to `main`.
In practice we never used that — the Spec Kit feature branch merged to `main`
early (just the spec artifacts), and every implementation slice was cut off
`main` and PR'd straight back to `main`. Docs and reality diverged, which made the
branch numbering feel wrong.

## Decision

**`main` is the only integration line.** Every branch — the Spec Kit
`NNN-short-name` feature branch, `feat/NNN-<slice>` implementation slices, and
`docs/`/`ci/`/`chore/` branches — is cut off `main` and merged back to `main` via
PR. There is no long-lived per-feature integration branch. `NNN` is the Spec Kit
feature id shared by all slices of that feature (`feat/001-<slice>`). CI gates
every PR. `docs/BRANCHING.md` is the operational reference.

## Consequences

- Simple, linear history; fast integration; one place that's always green.
- No "where does this merge to?" ambiguity.
- Loses the (unused) ability to stage a whole feature before touching `main` —
  acceptable for this scope.

## Alternatives considered

- **GitFlow** (`develop`/`release`/`hotfix`) — ceremony without payoff here.
- **Per-feature integration branch** (the original doc) — we never used it; it
  added a redundant merge layer.
