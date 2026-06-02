# Branching Strategy

Trunk-based development with short-lived branches. The model is chosen to align
with the two tools already in play — **Spec Kit** (which cuts a numbered feature
branch per feature) and **Superpowers** (which can run port-adapter subagents in
parallel git worktrees) — and with the project constitution rule that *spec,
decisions, plan, and tasks are committed and versioned*.

We deliberately avoid GitFlow (`develop` + `release` + `hotfix` lines): for a
single feature on a tight time box it adds ceremony without payoff. One trunk,
short-lived branches, fast integration.

## The lines

| Branch | Lifetime | Purpose |
| --- | --- | --- |
| `main` | permanent | **Protected trunk.** Always green, always `docker-compose up`-runnable. The baseline scaffolding (Spec Kit, Superpowers config, `PLAN.md`, docs) lives here. No direct pushes — everything lands via PR. |
| `NNN-short-name` | per feature | **Spec Kit feature branch**, cut off `main` by `/speckit-specify` (e.g. `001-document-annotation`). Holds `specs/NNN-short-name/{spec,plan,tasks}.md` and acts as the integration line while the feature is built. |
| `feat/NNN-<slice>` | hours | **Implementation slice / port adapter**, cut off the feature branch. One per vertical slice or per independent port (`feat/001-parsing-adapter`, `feat/001-llm-adapter`). Merges back up, then deletes. |

## Rules

1. **Protect `main`.** No direct commits. Merge only via PR with tests green.
   (Enable branch protection on the GitHub remote once it exists.)
2. **Let Spec Kit own the feature branch.** Do not hand-create the `NNN-*`
   branch — `/speckit-specify` creates it (it numbers from `specs/` and checks
   out from the current branch, so run it from an up-to-date `main`).
3. **One concern per slice branch.** Vertical slices, not horizontal layers:
   a slice branch carries a thin end-to-end capability, not "all the models" or
   "all the routers." Port adapters (parsing, llm, blob, store) are the safe unit
   to parallelize — one branch/worktree each, given a fixed port interface. Keep
   the **domain core and composition root sequential** on the feature branch.
4. **Parallel work uses worktrees, not long-lived branches.** When Superpowers
   fans out subagents along ports, each runs in its own `git worktree` so they
   don't collide. Reintegrate promptly; don't let a branch drift.
5. **Conventional Commits.** `feat:`, `fix:`, `test:`, `chore:`, `docs:`,
   `refactor:`. Small commits, each green. **Never commit on red** — TDD means
   the red test and its green implementation can share a commit, but a pushed
   commit must build and pass.
6. **Integrate forward, rebase don't back-merge.** Rebase slice branches on the
   feature branch (and the feature branch on `main`) to keep history linear.
   **Squash-merge** slice branches into the feature branch; merge the feature
   branch into `main` via PR.
7. **Delete merged branches.** Slice and feature branches are disposable once
   merged. The history lives in `main`.

## Typical flow

```bash
# 0. main holds the scaffolding (this commit).
git switch main

# 1. Spec Kit authors on a feature branch (it creates + checks out the branch):
#    /speckit-specify ... -> branch 001-document-annotation, specs/001-.../spec.md
#    /speckit-plan, /speckit-tasks -> plan.md, tasks.md
git add specs/ && git commit -m "docs: spec, plan, tasks for annotation service"

# 2. Implement a slice off the feature branch:
git switch -c feat/001-domain-core 001-document-annotation
# ... TDD: red test + green impl ...
git commit -m "test: Job/StageResult domain invariants" \
           -m "feat: domain entities with tenant_id"

# 3. Port adapters in parallel (worktrees keep them isolated):
git worktree add ../colophon-parsing feat/001-parsing-adapter
git worktree add ../colophon-llm     feat/001-llm-adapter

# 4. Squash-merge slices up, then the feature branch to main via PR.
git switch 001-document-annotation && git merge --squash feat/001-domain-core
gh pr create --base main --head 001-document-annotation
```
