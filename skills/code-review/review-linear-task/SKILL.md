---
name: review-linear-task
description: >-
  Review the implementation of a Linear task: fetch the issue via the Linear
  MCP server, understand its requirements and acceptance criteria, locate the
  code changes that implement it (branch, PR, or working diff), and review the
  changes against the task — checking completeness, correctness, and code
  quality. Use when the user asks to review a Linear task/issue/ticket, check
  whether an implementation matches its Linear ticket, or review the code for
  an issue ID like ABC-123. First verifies the current repo actually matches
  the task's project — on a mismatch it stops and helps the user find the
  right project instead of reviewing the wrong one. If the task has a branch,
  checks out that branch
  and merges local main into it first so the review runs against latest main,
  and checks whether the task is already implemented on main. Non-code tasks
  (info gathering, decisions, ops) get a required-actions summary from the
  issue comments instead of a code review; database changes (adding, removing
  or renaming fields, migrations) get an extra-careful model-vs-migration
  review. Ends with a verdict (Complete / Incomplete / Needs changes) and a
  findings list;
  optionally posts a summary comment to Linear and offers to merge the branch
  into main and push, each after user confirmation.
---

# Review Linear Task

Given a Linear issue, review the code that implements it against what the task actually asks for. The deliverable is a review report — do **not** fix code, commit, or change the issue state unless the user explicitly asks. The only merges in this flow are the two defined below: main into the task branch before reviewing, and (after confirmation) the task branch into main at the end.

## Before you start

- You need the Linear MCP server (`mcp__linear-server__*` tools). If its tools are unavailable, stop and tell the user to connect Linear.
- Mostly read-only: fetching issues, reading diffs, and reading code are fine. The two allowed repo writes are part of this skill's flow: merging local `main` into the task branch before the review (Step 2), and merging the task branch into `main` + pushing at the very end — the latter **only** after the user confirms. Anything else that writes to Linear (comments, status changes) or to the repo requires explicit user confirmation first.
- Before switching branches, run `git status` — if the working tree is dirty, stop and ask the user how to handle the uncommitted changes (stash, commit, or abort).
- If no issue is specified, ask for the issue identifier (e.g. `ENG-123`) or infer it from the current branch name (`eng-123-add-login`) and confirm the guess with the user.

## Step 1 — Fetch the task

Use the Linear MCP tools:

1. Get the issue (`get_issue`) — title, description, state, assignee, labels, estimate.
2. List its comments (`list_comments`) — requirements often get refined in comments; later comments override the original description.
3. Note any linked resources on the issue: attached PRs, branch names, related issues, parent/sub-issues.

From this, write down (for yourself) the **requirement checklist**: every concrete behavior, edge case, and acceptance criterion the task demands. If the description is vague ("improve the settings page"), extract what is checkable and flag the rest as unverifiable in the final report.

### Verify you're in the right project

The skill may have been invoked in a repo that has nothing to do with the task. Before touching git, check that the current repository matches the task:

- Compare the task's Linear **team/project name**, attached repo/PR links, branch names, and any file paths or technologies mentioned in the description against the current repo (folder name, `git remote -v`, the actual files present).
- If the task mentions files, modules, or a stack that clearly don't exist here (e.g. the task is about a Flutter app and this is a Node API), treat it as a mismatch.

On a mismatch, **do not proceed** — no checkout, no merge, no review. Tell the user:

1. Which project the task appears to belong to, and why the current repo doesn't match.
2. That they should re-run the skill from the right project directory.
3. Offer to help locate the project on their machine, e.g.:

   ```bash
   # local — search likely locations for the repo by name
   mdfind -name "PROJECT_NAME" | grep -v Library | head
   find ~/Desktop ~/Projects ~/Documents -maxdepth 4 -type d -iname "*PROJECT_NAME*" 2>/dev/null
   ```

Only continue past this point when the repo plausibly matches the task, or the user explicitly confirms it's the right one.

### If the task is not a code task

Some tasks aren't code changes at all — gathering information, making a decision, contacting someone, configuring a service, writing docs. If the description and comments show there's nothing to implement in the repo:

1. Read **all** comments carefully — for these tasks the comments usually carry the real state (what's been tried, what's blocked, who's waiting on whom).
2. Skip the git/review steps entirely.
3. Report back to the user instead:
   - What the task is actually asking for, in one or two sentences.
   - Current state based on the comments (done / blocked / waiting on X).
   - **Actions required** — a concrete numbered list of what needs to happen next, who can do each action (the user, you, or a third party), and which ones you could do now if asked.

Then stop — do not invent a code review for a task that has no code.

## Step 2 — Locate the implementation

Find the code changes that claim to implement the task, in this order of preference:

1. **PR / diff attached to the issue** — use the issue's attachments/links, or `list_diffs` / `get_diff` if the workspace uses Linear diffs.
2. **Branch named after the issue** — look for the issue identifier in branch names:
   ```bash
   git branch -a | grep -i ISSUE_ID
   ```
3. **Current branch / working tree** — if the user says the work is local, review the branch's diff against the default branch:
   ```bash
   git log main..HEAD --oneline
   git diff main...HEAD
   ```

If you cannot find any related changes, skip to Step 3 anyway — the task may already be implemented on `main` — and say so in the final report.

### Sync the task branch with main

If the task has a branch, check it out and merge **local** `main` into it so the review always runs against a branch that is up to date with the latest main:

```bash
git checkout TASK_BRANCH
git merge main
```

- If the merge completes cleanly (or the branch was already up to date), continue.
- If the merge has **conflicts**, do not resolve them silently: run `git merge --abort`, then show the user the conflicting files and ask whether they want you to resolve the conflicts or handle it themselves. Do not proceed with the review on a half-merged tree.
- After a successful merge, the diff to review is `git diff main...HEAD` — the task's own changes, not main's.

## Step 3 — Check the task isn't already implemented

Before reviewing the branch, check whether `main` already implements the task. Using the requirement checklist from Step 1, search main's code for the behaviors the task asks for:

```bash
git grep -n "RELEVANT_TERM" main -- .
```

and read the relevant files on `main` where needed.

- If **all** requirements already exist on `main`, stop: report that the task appears already implemented (with `file:line` evidence per requirement), and that the branch may be redundant or duplicate work. Let the user decide what to do with the branch.
- If only some exist, note which — the review in Step 4 should focus on what the branch actually adds.

## Step 4 — Review the changes against the task

Work through the diff with the requirement checklist from Step 1. For every changed file, read enough surrounding code (not just the diff hunks) to judge correctness in context.

Check, in order of importance:

1. **Completeness** — is every requirement from the checklist implemented? List each requirement as ✅ done / ⚠️ partial / ❌ missing, with file references.
2. **Correctness** — does the implementation actually do what the task asks? Trace the main flows; look for edge cases the task mentions (and obvious ones it doesn't: empty input, errors, concurrency, permissions).
3. **Scope** — changes unrelated to the task (drive-by refactors, unrelated files). Flag them; they belong in another task.
4. **Regressions** — could the change break existing behavior? Check callers of modified functions, changed signatures, altered defaults, migrations.
5. **Tests** — are new behaviors covered? If the repo has a test suite, run it (or the relevant subset) and report the result honestly, including failures.
6. **Quality** — naming, duplication, dead code, error handling, and consistency with the surrounding codebase. Keep this section short; it is secondary to completeness and correctness.

### Extra attention: database changes

If the diff touches the database — migrations, schema files, model/entity definitions, adding, removing, or renaming fields — treat it as high-risk and review it with extra care. Verify that the model is right, field by field:

- **Model ↔ migration ↔ task agree.** The model/entity definition, the migration, and what the task asked for must all match: field names, types, nullability, defaults, constraints, indexes, and relations. A migration that doesn't match its model is a Blocker.
- **Removed fields** — is anything still reading or writing them (queries, serializers, forms, API responses, background jobs)? Does dropping the column lose data that should have been migrated or archived first?
- **Added fields** — correct type and size for the data? Nullable or defaulted so existing rows and old app versions don't break on deploy? Indexed if it's queried/filtered on?
- **Renames** — done as a real rename (data preserved), not drop-and-add (data lost)?
- **Migration safety** — is there a down/rollback path? Will it run safely on a table with existing production data (backfills, locks on large tables)?
- **Every consumer updated** — grep for the old and new field names across the whole repo; stale references in raw SQL, fixtures, seeds, and tests count.

Report any doubt here as a finding — for schema changes, "probably fine" is not good enough; say exactly what you verified and what you couldn't.

For any suspected bug, verify it before reporting: re-read the code path, and where practical reproduce it with a quick test or script. Do not report "plausible" issues as confirmed.

## Step 5 — Report

Present the review to the user in this format:

```markdown
## Review: ISSUE_ID — ISSUE_TITLE

**Verdict**: Complete / Incomplete / Needs changes

### Requirements
- ✅ REQUIREMENT — where it's implemented (`file:line`)
- ⚠️ REQUIREMENT — what's partial and what's left
- ❌ REQUIREMENT — missing entirely

### Findings
1. **[Blocker|Major|Minor]** One-sentence issue — `file:line`, why it's wrong, concrete failure scenario, suggested fix.

### Out of scope / notes
- Unrelated changes, unverifiable requirements, follow-up suggestions.
```

Verdict rules:

- **Complete** — all requirements ✅, no Blocker/Major findings.
- **Needs changes** — requirements met but Blocker/Major findings exist.
- **Incomplete** — one or more requirements ⚠️/❌.

## Step 6 — Optional: post the review to Linear

Only after the user confirms:

- Post the report as a comment on the issue (`save_comment`), trimmed to what teammates need — verdict, requirement checklist, findings.
- Do **not** change the issue's state, assignee, or labels unless the user explicitly asks for that too.

## Step 7 — Offer to merge into main and push

After everything else is done, ask the user whether they want the task branch merged into `main` and pushed. Never merge or push without their explicit yes in this conversation.

- If the verdict was **Needs changes** or **Incomplete**, still ask — but restate the Blocker/Major findings or missing requirements in the question so the user decides with eyes open.
- On yes:

  ```bash
  git checkout main
  git merge TASK_BRANCH
  git push
  ```

  The branch already contains latest main from Step 2, so this merge should be conflict-free; if it somehow conflicts, abort and report instead of resolving silently.
- Confirm the result with `git log -1 --oneline` and `git status`, and report what was merged and pushed.
- Do not delete the task branch unless the user asks.

## Safety checklist

- [ ] Issue and its comments were read before reviewing code
- [ ] Current repo verified to match the task's project — stopped on mismatch instead of proceeding
- [ ] Working tree was clean (or user decided) before switching branches
- [ ] Task branch merged with local main before the review; conflicts surfaced, never silently resolved
- [ ] Checked main first for an existing implementation before reviewing the branch
- [ ] Non-code tasks answered with a required-actions summary, not a forced code review
- [ ] Database changes reviewed field by field: model ↔ migration ↔ task all agree
- [ ] Reviewed the changes that belong to this task, not unrelated code
- [ ] Every reported bug was verified, not just pattern-matched
- [ ] Test results (if run) reported honestly, including failures
- [ ] Nothing posted to Linear without explicit confirmation
- [ ] Merge into main + push only after the user's explicit yes
