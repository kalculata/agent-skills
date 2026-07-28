---
name: implement-linear-task
description: >-
  Implement a Linear task end to end: fetch the issue, its sub-issues, and
  comments via the Linear MCP server, build a requirement checklist, verify
  each repo matches its sub-issue, check whether the work already exists on
  main, move the parent and sub-issues to In Progress when work starts, create
  or check out per-repo task branches (each sub-issue's own gitBranchName when
  sub-issues exist), agree a plan with the user, then write the code. Use when
  the user asks to implement, build, work on, or start a Linear
  task/issue/ticket, or to do the work for an issue ID like ABC-123. Never
  implements on main. Handles parent + sub-issue trees and multi-repo work
  (one branch/PR per sub-issue, linked by sub-issue ID). Moves sub-issues to
  Done when their work is verified or merged; closes the parent when all
  sub-issues are done. Non-code tasks get a required-actions summary instead
  of code. Verifies with tests/build/lint, then — each only after explicit
  user confirmation — commits, pushes, opens PRs, posts Linear comments, and
  offers to merge.
---

# Implement Linear Task

Given a Linear issue, do the work it describes and land it on task branch(es). The deliverable is working, verified code on branch(es) — plus, only with the user's explicit yes, pushed PR(s), Linear comment(s), and merge into `main`.

## Before you start

- You need the Linear MCP server (`mcp__linear-server__*` tools). If its tools are unavailable, stop and tell the user to connect Linear.
- This skill **writes code**. That's expected. What still needs explicit user confirmation, every time: pushing, opening a PR, commenting on Linear, and merging into `main`.
- Run `git status` first in every repo you will touch. If any working tree is dirty, stop and ask the user how to handle the uncommitted changes (stash, commit, or abort) before switching branches.
- If no issue is specified, ask for the issue identifier (e.g. `ENG-123`) or infer it from the current branch name (`eng-123-add-login`) and confirm the guess with the user.
- Never change assignee or labels.

### Linear status changes this skill makes

| When | What moves | How |
| --- | --- | --- |
| Work starts (Step 3) | Parent + every sub-issue still in Backlog/Todo | → **In Progress** |
| Sub-issue work verified or PR merged (Step 11) | That sub-issue | → **Done** |
| All sub-issues Done | Parent | → **Done** |
| No sub-issues; PR merged + user asked to close | Parent | → **Done** (or rely on GitHub automation first, then fix up if stuck) |

Linear **does not cascade** parent ↔ child status, and GitHub integration links PRs **only to issue IDs appearing in the branch name or PR title**. A PR titled `DEV-383: …` closes DEV-383 but leaves sub-issues DEV-400 / DEV-401 open. This skill accounts for that explicitly.

### Never implement on main

All task code goes on a **task branch**, never on `main` — even when the change is one line, the user says "just do it quickly", or `main` already has related work.

**Forbidden:** committing task changes directly to `main`.

If an issue already has a branch or an open PR, that branch is the source of truth — check it out and continue the work there. Do not start a second branch for the same issue.

## Step 1 — Fetch the task and sub-issues

Use the Linear MCP tools:

1. Get the issue (`get_issue`, `includeRelations: true`) — title, description, state, assignee, labels, estimate, `gitBranchName`, attachments.
2. List its comments (`list_comments`) — later comments override the original description.
3. **Discover sub-issues.** Linear does not always return children on `get_issue`. Also run `list_issues` with queries like the parent ID, or fetch likely child IDs from the parent description. Collect every issue whose `parentId` matches the given issue.
4. For **each sub-issue**, record: ID, title, description, status, `gitBranchName`, repo hint (e.g. `Repo: music_app_api`), key files.

Build two artifacts:

- **Requirement checklist** — every concrete behavior, edge case, and acceptance criterion (parent description + sub-issue descriptions + comments).
- **Work map** — which sub-issue (or the parent, if no sub-issues) maps to which repo, branch name, and PR identifier.

### Parent vs sub-issue: which ID goes where

| Artifact | Use parent ID | Use sub-issue ID |
| --- | --- | --- |
| Git branch name (when sub-issues exist) | No — use each sub-issue's `gitBranchName` | Yes |
| PR title | Mention parent in body only | **Yes — sub-issue ID in title** |
| Commit message | Optional secondary mention | **Yes — primary ID for that repo's commit** |
| Linear PR attachment / auto-link | Unreliable for children if only parent ID used | **Yes — one PR per sub-issue ID** |

When the user gives a **parent** issue and sub-issues exist, implement against the parent's checklist but **track and close work through the sub-issues**.

If the user gives a **sub-issue** directly, treat it as the active work item; still fetch the parent for context and update the parent to Done when all siblings are Done.

### Verify you're in the right project

Before touching git, check that the current repository matches the **sub-issue** you are about to implement (or the parent, if there are no sub-issues):

- Compare repo name, `git remote -v`, stack, and file paths in the sub-issue description.
- If the task spans multiple repos (e.g. API sub-issue + dashboard sub-issue), implement each part from the matching repo — do not put API and dashboard changes on one branch in one repo.

On a mismatch, **do not proceed** in that repo. Tell the user which repo the sub-issue belongs to and offer to locate it locally.

### If the task is not a code task

Read all comments, skip git/implementation, and return a required-actions summary. Then stop.

## Step 2 — Check whether it's already implemented

Before writing anything, check `main` (or existing task branches) against the requirement checklist:

```bash
git grep -n "RELEVANT_TERM" main -- .
git branch -a | grep -i ISSUE_ID
gh pr list --search "ISSUE_ID" --state all
```

Do this **per sub-issue** when sub-issues exist.

- If **all** requirements already exist, stop with `file:line` evidence. Mark the sub-issue(s) and parent Done if the user confirms.
- If **some** exist, implement only the gap.
- If an existing branch or open PR already has partial work for a sub-issue, continue on that branch.

## Step 3 — Move issues to In Progress, then set up branches

### Move to In Progress

Do this **before** writing code.

1. `list_issue_statuses(team: TEAM)` — find the started-type status (prefer the one named "In Progress").
2. Move the **parent** to In Progress if its status type is `backlog` or `unstarted`.
3. Move **every sub-issue** to In Progress if its status type is `backlog` or `unstarted`.
4. Leave issues already In Progress, In Review, Done, Canceled, or Duplicate unchanged — never move backwards.

If a status update fails (permissions), say so and continue.

### Set up task branch(es)

For **each repo** in the work map, from up-to-date `main`:

```bash
git checkout main
git pull
git checkout -b SUB_ISSUE_GIT_BRANCH_NAME   # prefer sub-issue gitBranchName
```

Rules:

- **Sub-issues exist:** use each sub-issue's `gitBranchName` in its repo — not the parent's branch name. Example: DEV-401 branch in `music_app_api`, DEV-400 branch in `music_app_dashboard`, even when the user invoked the skill with parent DEV-383.
- **No sub-issues:** use the parent issue's `gitBranchName`.
- **Same repo, multiple sub-issues:** one branch per sub-issue unless an open PR already exists for one of them.
- If merging `main` into an existing branch conflicts, abort and ask the user.

State the work map in the plan (Step 4): repo → sub-issue ID → branch name.

## Step 4 — Plan before writing code

Read enough of each codebase to implement in its idiom. Show a short plan:

- Repos and sub-issues involved
- Files to add or change per repo
- Which requirement each change satisfies
- Deploy order when API + client both change (API first)
- Ambiguities and assumptions

Wait for go-ahead on ambiguities, schema changes, or materially different approaches. For small unambiguous tasks, state the plan and proceed.

## Step 5 — Implement

Write code on the correct task branch per repo. Follow existing conventions. Implement the checklist only — no drive-by refactors.

- Handle named edge cases plus obvious ones (empty input, errors, permissions).
- Add or update tests when the repo has a test suite.
- Update every caller when signatures or response shapes change.
- No secrets in code.

### Extra attention: database changes

Model ↔ migration ↔ task must agree. Every consumer updated. Ask before migrating if unclear.

## Step 6 — Verify

Do not report done on unverified code.

1. Run tests, build, and linter **per repo touched**.
2. Exercise the behavior when practical.
3. Walk the checklist with `file:line` evidence **per sub-issue**.

Report failures honestly.

## Step 7 — Commit

Commit on each task branch. Match the repo's commit style.

- Stage only task files — never `git add -A` when unrelated changes exist.
- **Include the sub-issue ID** in the commit message when sub-issues exist (e.g. `DEV-401: …`). Mention the parent ID optionally in the body.

## Step 8 — Push and open PR(s)

Ask the user first. Only on their explicit yes.

Push and open **one PR per sub-issue** (one per repo):

```bash
git push -u origin SUB_ISSUE_BRANCH
gh pr create --base main --head SUB_ISSUE_BRANCH \
  --title "SUB_ISSUE_ID: short title" \
  --body "..."
```

PR rules:

- **Title must contain the sub-issue ID** (e.g. `DEV-401: …`), not only the parent ID — so Linear attaches the PR to the correct issue and automation can advance it.
- Body: what changed, how verified, link to the **sub-issue** URL, mention parent issue if helpful, note deploy order for multi-repo work.
- After opening, verify in Linear that the PR attachment landed on the **sub-issue**. If only the parent moved, tell the user — do not assume children updated.
- If `gh` is unavailable, give the compare URL.

### Multi-repo deploy order

When API and dashboard both change, state in both PR bodies: **merge and deploy API before dashboard**.

## Step 9 — Report

```markdown
## Implemented: PARENT_ID — PARENT_TITLE

**Status**: Complete / Partial / Blocked

### Sub-issues
- ✅ SUB_ID — repo — PR URL — status
- ⚠️ SUB_ID — what's left

### Requirements
- ✅ REQUIREMENT — `file:line` (SUB_ID if applicable)

### Changes
- `repo/path` — what changed

### Verification
- Commands run and results per repo

### Notes
- Assumptions, deploy order, automation gaps
```

## Step 10 — Close sub-issues and parent in Linear

After verification — or after the user confirms merge — update Linear statuses explicitly. **Do not rely on parent PR automation to close sub-issues.**

1. For each sub-issue whose work is verified or merged: `save_issue(id: SUB_ID, state: "Done")`.
2. Re-fetch sub-issues. When **all** are Done, `save_issue(id: PARENT_ID, state: "Done")`.
3. If GitHub automation already closed the parent but sub-issues are still open, close the sub-issues now and explain why they were stuck.

When posting an optional summary comment (`save_comment`), do it on the **sub-issue** (and parent if useful). Do not change assignee or labels.

## Step 11 — Offer to merge into main

Ask the user before merging. Never merge without explicit yes.

- Merge **API PRs before client/dashboard PRs** when both exist.
- Prefer `gh pr merge` over local merge.
- After merge, run Step 10 if not already done — merged sub-issues → Done, then parent when all children are Done.
- Confirm with `git log -1 --oneline` and `git status` per repo.
- Do not delete task branches unless the user asks.

## Safety checklist

- [ ] Parent issue, all sub-issues, and all comments read before coding
- [ ] Work map built: sub-issue → repo → branch → PR ID
- [ ] Each repo verified against its sub-issue before coding there
- [ ] Checked whether work already exists before re-implementing
- [ ] Working trees clean (or user decided) before branching
- [ ] All work on task branches from up-to-date `main` — nothing on `main`
- [ ] Sub-issue `gitBranchName` used per repo (not parent branch when sub-issues exist)
- [ ] Parent + Backlog/Todo sub-issues moved to In Progress before coding
- [ ] PR titles use **sub-issue IDs** when sub-issues exist
- [ ] Verified Linear PR attachments landed on sub-issues, not just parent
- [ ] Sub-issues marked Done after verify/merge; parent Done when all children Done
- [ ] Tests/build/lint run per repo; results reported honestly
- [ ] Every requirement has `file:line` evidence before claiming Complete
- [ ] Nothing pushed, no PR opened, no merge without explicit user confirmation
- [ ] Assignee and labels untouched
