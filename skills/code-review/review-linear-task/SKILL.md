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
  and checks whether the task is already implemented on main — if it is and
  no merge is needed, offers to close the branch's open PR with gh. Non-code
  tasks
  (info gathering, decisions, ops) get a required-actions summary from the
  issue comments instead of a code review; database changes (adding, removing
  or renaming fields, migrations) get an extra-careful model-vs-migration
  review. Ends with a verdict (Complete / Incomplete / Needs changes) and a
  findings list;
  optionally posts a summary comment to Linear and offers to merge the branch
  into main and push, each after user confirmation. Never re-implement on main
  when the task already has a branch or open PR — always work through the task
  branch (rebase/merge main, fix there, then merge the branch or PR into main).
---

# Review Linear Task

Given a Linear issue, review the code that implements it against what the task actually asks for. The deliverable is a review report — do **not** fix code, commit, or change the issue state unless the user explicitly asks. The only merges in this flow are the two defined below: main into the task branch before reviewing, and (after confirmation) the task branch into main at the end. If the user asks to proceed after the review, always use the task branch — never re-implement the same changes directly on `main` while a task branch or open PR exists.

## Before you start

- You need the Linear MCP server (`mcp__linear-server__*` tools). If its tools are unavailable, stop and tell the user to connect Linear.
- Mostly read-only: fetching issues, reading diffs, and reading code are fine. The two allowed repo writes are part of this skill's flow: merging local `main` into the task branch before the review (Step 2), and merging the task branch into `main` + pushing at the very end — the latter **only** after the user confirms. Anything else that writes to Linear (comments, status changes) or to the repo requires explicit user confirmation first.
- Before switching branches, run `git status` — if the working tree is dirty, stop and ask the user how to handle the uncommitted changes (stash, commit, or abort).
- If no issue is specified, ask for the issue identifier (e.g. `ENG-123`) or infer it from the current branch name (`eng-123-add-login`) and confirm the guess with the user.

### Never bypass the task branch

If the Linear issue has a **task branch** and/or **open PR**, that branch is the source of truth for the implementation. **Never** re-implement the same work by editing `main` directly — even when:

- The user says "ignore the review and continue" or "just merge it"
- The branch is stale, behind `main`, or has merge conflicts
- Review findings suggest fixes or a different approach
- The branch code looks incomplete or lower quality than a fresh rewrite

**Forbidden:** committing task changes directly to `main` while a task branch or open PR still exists for that issue.

**Required workflow when proceeding after review:**

1. Identify the task branch from the issue (`gitBranchName`, PR `headRefName`, or `git branch -a | grep -i ISSUE_ID`).
2. Check out the task branch (stash or commit unrelated local changes first).
3. Merge **local** `main` into the task branch (or rebase onto `main` if that is the repo norm).
4. Apply any fixes or improvements **on the task branch**, not on `main`.
5. Push the updated task branch.
6. Merge into `main` via the existing PR (`gh pr merge`) or `git checkout main && git merge TASK_BRANCH && git push` — only after the user confirms.
7. If the PR becomes redundant only because the branch was fully superseded, close it with a comment — never leave an open PR while the same work landed on `main` through a separate direct commit.

Direct commits to `main` for a Linear task are allowed **only** when Step 2 found **no** task branch and **no** open PR for that issue.

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

- If **all** requirements already exist on `main`, stop the review: report that the task appears already implemented (with `file:line` evidence per requirement), and that the branch may be redundant or duplicate work.
- If only some exist, note which — the review in Step 4 should focus on what the branch actually adds.

### Close a redundant PR

When the task is already implemented on `main` and no merge is needed, check whether the task branch has an open PR and offer to close it:

```bash
gh pr list --head TASK_BRANCH --state open
```

If one exists, show it to the user and ask whether to close it. Only on their explicit yes:

```bash
gh pr close PR_NUMBER --comment "Closing: ISSUE_ID is already implemented on main (see review). No merge needed."
```

- Close, don't merge — `gh pr close` leaves the branch's commits unmerged, which is the point.
- Never close a PR without confirmation, and never delete the branch (`--delete-branch`) unless the user asks for that separately.
- If `gh` is unavailable or not authenticated, tell the user the PR should be closed manually and give them the link.

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
- If an **open PR** exists for the task branch, prefer merging through that PR (`gh pr merge PR_NUMBER`) so GitHub records the merge correctly. Use a direct `git merge TASK_BRANCH` into `main` only when there is no PR or the user asks for that path.
- On yes, follow the **Never bypass the task branch** workflow above — do not rewrite the changes on `main`:

  ```bash
  git stash push -m "wip" -- unrelated paths if needed
  git checkout TASK_BRANCH
  git merge main
  # fix conflicts and review findings on the task branch, then:
  git push -u origin TASK_BRANCH
  gh pr merge PR_NUMBER   # when a PR exists
  # or, when merging locally without a PR:
  git checkout main
  git merge TASK_BRANCH
  git push
  git stash pop           # if you stashed
  ```

  The branch should contain latest `main` from Step 2 (or a fresh merge in this step), so the merge into `main` should be conflict-free; if it conflicts, abort and report instead of resolving silently on `main`.
- Confirm the result with `git log -1 --oneline` and `git status`, and report what was merged and pushed (include PR URL when merged via PR).
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
- [ ] Did not re-implement on `main` while a task branch or open PR existed for the issue
- [ ] Merge into main + push only after the user's explicit yes, through the task branch or its PR
- [ ] Redundant PRs closed (not merged) only after the user's explicit yes, branch left intact
