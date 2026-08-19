---
name: ship
description: Ship a pi-matrix release — reflect this session's decisions into PRODUCT.md/TODO.md/README.md, run the project's lint & build checklist, bump the patch version tag, and push everything (commits + tag) to origin. Use when the user says "ship", "ship it", "发个版本", "推送更新", or explicitly invokes /ship.
---

# Ship

Wrap up the working tree and cut a release: docs reflect what actually changed,
the build is verified green, the tag is bumped, everything lands on `origin/main`.
This is specific to pi-matrix's own conventions — no CHANGELOG.md, no VERSION file,
no PR (direct push to main), annotated git tags are the version of record.

## When to use

- The user says "ship", "ship it", "发布", "发个版本", "推送更新"
- Explicitly invoked as `/ship`

## Process — do these in order, stop at the first failure

### Step 1 — Update project docs

This project keeps exactly three docs: `README.md`, `PRODUCT.md`, `TODO.md` (see
`CLAUDE.md`). Before touching git, make sure they reflect what actually happened —
don't skip this because "nothing to write", check first:

- **`PRODUCT.md`** — any architecture/strategy/design decision made in this session
  that isn't written down yet? This file is the design-of-record; a decision that
  only exists in conversation is a decision that gets re-litigated next session.
- **`TODO.md`** — mark finished items done and remove them (its own rule: completed
  items get their conclusion written into `PRODUCT.md` and are removed from here,
  not left checked-off as clutter). Add anything discovered this session that isn't
  tracked yet.
- **`README.md`** — only touch if user-facing behavior or positioning actually
  changed. Most ships won't touch this file — don't force an edit here.
- **`CLAUDE.md`** — only touch if architecture/commands changed enough that a fresh
  Claude Code session would get misled by the current text.

Do not invent content. Every line added here should trace to something that was
actually decided or built this session, not filler to make the section look complete.

### Step 2 — Lint & build checklist

Run the full checklist every time — the repo is small enough that this is cheap,
and partial checks have a way of missing the thing that actually broke:

```bash
cd cloud/dashboard && npx tsc --noEmit && npm run build && cd ../..
python3 -m compileall -q cloud/api cloud/message cloud/orchestrator cloud/executor deploy/scripts
bash -n deploy/scripts/*.sh agent/installer/install.sh agent/updater/update.sh
```

If `bench/` has changed files this ship, also check the runner and any new/edited
task manifests parse:

```bash
node --check bench/runner/run.mjs
node -e "require('yaml').parse(require('fs').readFileSync('<changed task.yaml>', 'utf8'))"  # per changed task.yaml
```

**If anything fails here, stop.** Report the failure plainly and do not proceed to
commit/tag/push a broken build. Fixing the failure is a separate task unless it's
trivial and obviously in-scope.

### Step 3 — Stage, review, commit

- Never `git add -A` / `git add .` — add specific files.
- After staging, run `git status` and eyeball the file list. **This matters more
  than usual now**: `PRODUCT.md` was brought under version control on 2026-08-19
  and this repo is public — before pushing, make sure nothing in the diff is
  content that shouldn't be world-readable (this is a standing check, not a
  one-time thing).
- Group unrelated changes into separate commits with real conventional messages
  (`type: description`, e.g. `docs:`, `feat:`, `fix:`, `chore:`) — don't squash
  everything pending into one "ship" commit. Match the style already in `git log`.
- No attribution footer / Co-Authored-By line — this repo's commits don't carry one
  (confirm with `git log -3 --format=%B` if unsure).

### Step 4 — Bump the tag

`/ship` always bumps the **patch** version by +0.0.1 — that's the "小版本" the user
asked for (MAJOR.MINOR.PATCH, last digit). If a minor or major bump is ever wanted,
that's a different, explicit ask (the user states the target version directly), not
the default here.

```bash
LATEST=$(git tag --sort=-v:refname | head -1)   # e.g. v0.9.0
# bump last number only: v0.9.0 -> v0.9.1
```

If `cloud/dashboard/` had any file changed in this ship, also bump
`cloud/dashboard/package.json`'s `version` (its own scheme, doesn't need to match
the repo tag) — otherwise leave it alone. An unchanged dashboard doesn't need a
version bump; a version bump with nothing behind it just makes the number
meaningless (this is why v0.9.0 didn't touch it — no dashboard code changed then).

Tag as annotated, not lightweight:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

### Step 5 — Push

```bash
git push origin main
git push origin vX.Y.Z
```

### Step 6 — Report

State plainly: what got committed (list the commits), the new tag, confirmation
both pushed. If Step 1 found nothing to change and Step 2 was all-green, say so —
don't pad the report.

## Notes

- This skill assumes the working tree only contains pi-matrix's own intended
  changes. If `git status` shows something unexpected (files you don't recognize,
  a change that doesn't match anything discussed this session), stop and ask
  before staging it — same rule as any other git operation.
- Patch-only bump policy is the default; a minor/major bump only happens when the
  user gives an explicit target version (e.g. v0.8.2 -> v0.9.0 was a direct
  instruction, not something `/ship` derived on its own — the skill's default is
  always patch, never minor/major). If that policy ever needs to change, update
  this file — don't just start improvising a different scheme.
- **Correction history**: the first real run of this skill (2026-08-19) mis-tagged
  v0.9.0 -> v0.10.0 as a minor bump. Corrected same-day: v0.10.0 deleted (local +
  remote), re-tagged as v0.9.1 on the same commit, this file fixed to patch-only.
