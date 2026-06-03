# Branching Strategy

**Trunk-based development.** One permanent branch (`main`); everything else is a
short-lived branch cut off `main` and merged straight back into `main` via PR.
There is **no long-lived per-feature integration branch** — `main` *is* the
integration line. This matches how the project is actually built and keeps history
simple under a tight time box.

We deliberately avoid GitFlow (`develop` + `release` + `hotfix`) and avoid stacking
work behind a feature branch: it adds ceremony without payoff here.

## The lines

| Branch | Lifetime | Purpose |
| --- | --- | --- |
| `main` | permanent | **Trunk + integration line.** Always green, always `docker-compose up`-runnable. Every branch merges here via PR. |
| `feat/NNN-<slice>` | hours–days | **Implementation slice / port adapter**, cut off `main`, merged back to `main`. `NNN` is the Spec Kit **feature id** (`001` = `specs/001-document-annotation`); the suffix names the slice (`feat/001-parsing-adapters`, `feat/001-llm-adapter`). |
| `NNN-short-name` | one PR | **Spec Kit feature branch** created by `/speckit-specify` (e.g. `001-document-annotation`). It carries the `specs/NNN-*/` artifacts and merges to `main` like any other branch — it is *not* kept alive as an integration line. |
| `docs/<topic>`, `ci/<topic>`, `chore/<topic>` | hours | Non-feature work (documentation, CI, tooling). Same flow: off `main`, PR to `main`. |

## Rules

1. **Keep `main` green.** Land work via PR with tests passing rather than
   committing directly. CI (`.github/workflows/ci.yml`) gates every PR.
2. **Branch off `main`, PR to `main`.** Including Spec Kit feature branches and
   implementation slices — `main` is the only integration point.
3. **`NNN` ties a slice to its feature.** All slices of the document-annotation
   feature are `feat/001-<slice>`. A genuinely new feature gets the next Spec Kit
   number (`002-…`) via `/speckit-specify`, and its slices become `feat/002-<slice>`.
4. **One concern per branch.** Vertical slices, not horizontal layers: a slice
   carries a thin end-to-end capability or one port adapter, not "all the models."
   Port adapters (parsing, llm, blob, store, messaging) are the safe unit to build
   independently given a fixed port interface; keep the **domain core and
   composition root coherent** (sequential, not split across racing branches).
5. **Optional: parallelize along ports with worktrees.** When fanning out
   port-adapter work, each can run in its own `git worktree` off `main` so they
   don't collide. Reintegrate promptly; don't let a branch drift.
6. **Conventional Commits.** `feat:`, `fix:`, `test:`, `chore:`, `docs:`,
   `refactor:`. Small commits, each green. **Never push on red.**
7. **Rebase on `main`, don't back-merge.** Keep history linear; rebase a slice on
   `main` before merging.
8. **Delete merged branches.** Branches are disposable once merged; the history
   lives in `main`.

## Typical flow

```bash
# 1. Spec Kit authors the spec on its own branch, then merges to main via PR:
#    /speckit-specify -> branch 001-document-annotation + specs/001-.../{spec,plan,tasks}.md
gh pr create --base main --head 001-document-annotation   # spec artifacts -> main

# 2. Implement a slice off main (TDD), then PR it straight to main:
git switch main && git pull
git switch -c feat/001-parsing-adapters
# ... red test -> green impl -> refactor ...
git commit -m "feat(parsing): real PDF + spreadsheet DocumentParser adapters (TDD)"
git push -u origin feat/001-parsing-adapters
gh pr create --base main --head feat/001-parsing-adapters

# 3. (Optional) independent port adapters in parallel worktrees, each off main:
git worktree add ../colophon-llm   -b feat/001-llm-adapter   main
git worktree add ../colophon-store -b feat/001-store-adapter main

# 4. After merge, delete the branch:
git push origin --delete feat/001-parsing-adapters && git branch -d feat/001-parsing-adapters
```
