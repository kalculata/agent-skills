---
name: implement-linear-task
description: >-
  Implement a Linear task end to end: fetch the issue and its comments via the
  Linear MCP server, build a requirement checklist, verify the current repo is
  the task's project, check whether the work already exists on main, create or
  check out the task branch (Linear's own branch name), agree a plan with the
  user, then write the code on that branch. Use when the user asks to
  implement, build, work on, or start a Linear task/issue/ticket, or to do the
  work for an issue ID like ABC-123. Never implements on main — always on the
  task branch, created from up-to-date local main. Non-code tasks (info
  gathering, decisions, ops) get a required-actions summary from the comments
  instead of code. Database changes (adding, removing or renaming fields,
  migrations) get extra care: model, migration and every consumer updated
  together. Verifies with the repo's own tests/build/lint before committing,
  reports failures honestly, then — each only after explicit user confirmation
  — commits, pushes and opens a PR, posts a summary comment to Linear, and
  offers to merge the branch into main.
---

# Implement Linear Task

Given a Linear issue, do the work it describes and land it on a task branch. The deliverable is working, verified code on a branch — plus, only with the user's explicit yes, a pushed PR, a Linear comment, and a merge into `main`.

## Before you start

- You need the Linear MCP server (`mcp__linear-server__*` tools). If its tools are unavailable, stop and tell the user to connect Linear.
- This skill **writes code**. That's expected. What still needs explicit user confirmation, every time: pushing, opening a PR, commenting on Linear, and merging into `main`.
- Run `git status` first. If the working tree is dirty, stop and ask the user how to handle the uncommitted changes (stash, commit, or abort) before switching branches.
- If no issue is specified, ask for the issue identifier (e.g. `ENG-123`) or infer it from the current branch name (`eng-123-add-login`) and confirm the guess with the user.
- Never change the issue's state, assignee, or labels. This skill's only Linear write is an optional summary comment at the end.

### Never implement on main

All task code goes on a **task branch**, never on `main` — even when:

- The change is one line
- The user says "just do it quickly"
- The branch would be short-lived anyway
- `main` is already dirty with related work

**Forbidden:** committing task changes directly to `main`.

If the issue already has a branch or an open PR, that branch is the source of truth — check it out and continue the work there. Do not start a second branch for the same issue, and do not rewrite the work fresh on `main`.

## Step 1 — Fetch the task

Use the Linear MCP tools:

1. Get the issue (`get_issue`) — title, description, state, assignee, labels, estimate, and its `gitBranchName`.
2. List its comments (`list_comments`) — requirements often get refined in comments; later comments override the original description.
3. Note linked resources: attached PRs, branch names, related issues, parent/sub-issues. A parent issue often carries context the sub-issue assumes.

From this, write down the **requirement checklist**: every concrete behavior, edge case, and acceptance criterion the task demands. This is what you implement against and what you verify against at the end.

If the description is vague ("improve the settings page"), do not guess your way through it — list what you extracted, state what's ambiguous, and ask the user to resolve the ambiguity before writing code.

### Verify you're in the right project

The skill may have been invoked in a repo that has nothing to do with the task. Before touching git, check that the current repository matches the task:

- Compare the task's Linear **team/project name**, attached repo/PR links, branch names, and any file paths or technologies mentioned in the description against the current repo (folder name, `git remote -v`, the actual files present).
- If the task mentions files, modules, or a stack that clearly don't exist here (e.g. the task is about a Flutter app and this is a Node API), treat it as a mismatch.

On a mismatch, **do not proceed** — no branch, no code. Tell the user:

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
2. Skip the git and implementation steps entirely.
3. Report back to the user instead:
   - What the task is actually asking for, in one or two sentences.
   - Current state based on the comments (done / blocked / waiting on X).
   - **Actions required** — a concrete numbered list of what needs to happen next, who can do each action (the user, you, or a third party), and which ones you could do now if asked.

Then stop — do not invent code for a task that has no code.

## Step 2 — Check whether it's already implemented

Before writing anything, check whether `main` (or the existing task branch) already does what the task asks. Using the requirement checklist, search the code for the behaviors involved:

```bash
git grep -n "RELEVANT_TERM" main -- .
git branch -a | grep -i ISSUE_ID
gh pr list --search "ISSUE_ID" --state all
```

and read the relevant files where the search points.

- If **all** requirements already exist, stop and report it with `file:line` evidence per requirement. Ask the user whether the task should just be closed instead — don't re-implement working code.
- If **some** exist, say which. Your implementation covers only the gap.
- If an existing branch or open PR already has partial work, continue **on that branch** rather than starting over.

## Step 3 — Set up the task branch

Start from an up-to-date `main`:

```bash
git checkout main
git pull
```

Then either resume the existing branch or create Linear's:

```bash
# existing branch for the issue
git checkout TASK_BRANCH
git merge main

# or a new one — prefer the issue's own gitBranchName from Step 1
git checkout -b TASK_BRANCH
```

- Use the issue's `gitBranchName` verbatim when creating a branch, so Linear links the branch and PR to the issue automatically. Only invent a name (`ISSUE_ID-short-description`, lowercase) if the issue has none.
- If merging `main` into an existing branch **conflicts**, do not resolve silently: run `git merge --abort`, show the user the conflicting files, and ask whether they want you to resolve them or handle it themselves.
- If `git pull` fails (no remote, no network), continue from local `main` and say so.

## Step 4 — Plan before writing code

Read enough of the codebase to implement in its idiom, not in the abstract: the modules the task touches, their callers, the existing patterns for the same kind of work (how other endpoints/screens/migrations in this repo are written), and the test conventions.

Then show the user a short plan **before** editing:

- Which files you'll add or change, and what each change does.
- Which requirement from the checklist each change satisfies.
- Anything the task left ambiguous, with the assumption you intend to make.
- Whether the change touches the database, public APIs, or anything else with blast radius.

Keep it short — a dozen lines, not a design doc. Wait for the user's go-ahead if the plan involves an ambiguity, a schema change, or a materially different approach than the task described. For a small, unambiguous task, state the plan and proceed.

## Step 5 — Implement

Write the code on the task branch, following the repo's existing conventions — naming, file layout, error handling, comment density, test style. Match the surrounding code rather than importing patterns from elsewhere.

Rules:

- **Implement the task, not around it.** Every requirement on the checklist, and nothing beyond it. No drive-by refactors, no unrelated file changes, no speculative abstraction — if you spot an unrelated problem, note it for the report instead of fixing it.
- **Handle the edge cases the task names**, plus the obvious ones it doesn't: empty input, error paths, permissions, concurrency.
- **Add or update tests** when the repo has a test suite, covering the new behavior — not just the happy path.
- **Update the callers.** Changed signatures, defaults, or shapes mean every call site, serializer, fixture, and doc that depends on them changes too. Grep for them; don't assume.
- **No secrets in code.** Keys, tokens, and credentials go in the repo's existing config/env mechanism.

### Extra attention: database changes

If the task touches the database — migrations, schema files, model/entity definitions, adding, removing, or renaming fields — treat it as high-risk and get it right field by field:

- **Model ↔ migration ↔ task must agree.** Field names, types, nullability, defaults, constraints, indexes, and relations must match across the model/entity definition, the migration, and what the task asked for.
- **Added fields** — correct type and size for the data. Nullable or defaulted so existing rows and older app versions don't break on deploy. Indexed if it will be queried or filtered on.
- **Removed fields** — find everything still reading or writing them (queries, serializers, forms, API responses, background jobs) and update it. If dropping the column loses data that matters, migrate or archive it first.
- **Renames** — do a real rename that preserves data, never drop-and-add.
- **Migration safety** — provide a down/rollback path, and consider what the migration does to a table with existing production data (backfills, locks on large tables).
- **Every consumer updated** — grep the whole repo for the old and new field names; raw SQL, fixtures, seeds, and tests count.

If any of this is unclear from the task, ask before migrating. A wrong migration is expensive to undo.

## Step 6 — Verify

Do not report the task as done on the strength of having written the code.

1. Run the repo's test suite, or the relevant subset if it's slow.
2. Run the build, type-check, and linter the repo uses.
3. Where practical, exercise the actual behavior the task describes (run the app, hit the endpoint, run a small script) rather than only asserting it should work.
4. Walk the requirement checklist one item at a time and confirm each is genuinely implemented, with the `file:line` to prove it.

Report results honestly. If tests fail, say so and show the output — fix the ones your change caused; for pre-existing failures, say they were already failing and leave them alone unless the user asks.

## Step 7 — Commit

Commit on the task branch with a message that matches the repo's existing commit style (`git log --oneline -20` to see it). If the `github-commit` skill is available, follow it for message style and staging.

```bash
git add PATHS          # stage only files that belong to this task
git commit
```

- Stage deliberately — never `git add -A` when the tree has unrelated changes.
- Include the issue identifier in the message if that's the repo's convention.
- Split into multiple commits if the work has genuinely distinct parts; one commit is fine otherwise.

## Step 8 — Push and open a PR

Ask the user first. Only on their explicit yes:

```bash
git push -u origin TASK_BRANCH
gh pr create --base main --head TASK_BRANCH --title "ISSUE_ID: TITLE" --body "..."
```

- The PR body should state what the task asked for, what changed, and how it was verified. Link the Linear issue.
- Including the issue identifier in the branch name or PR title lets Linear link the PR to the issue automatically.
- If `gh` is unavailable or unauthenticated, push the branch and give the user the compare URL to open the PR manually.
- If a PR already exists for the branch, push to it rather than opening a second one.

## Step 9 — Report

Present the result to the user in this format:

```markdown
## Implemented: ISSUE_ID — ISSUE_TITLE

**Status**: Complete / Partial / Blocked

### Requirements
- ✅ REQUIREMENT — where it's implemented (`file:line`)
- ⚠️ REQUIREMENT — what's done and what's left
- ❌ REQUIREMENT — not implemented, and why

### Changes
- `path/to/file` — what changed and why

### Verification
- Tests / build / lint commands run and their actual results, failures included

### Notes
- Assumptions made, unrelated problems spotted (not fixed), follow-ups worth their own task
```

Status rules:

- **Complete** — every requirement ✅ and verification passed.
- **Partial** — some requirements ⚠️/❌; say exactly which and what's needed to finish.
- **Blocked** — couldn't proceed (missing access, unresolved ambiguity, broken build); say what unblocks it.

Never report Complete on unverified code.

## Step 10 — Optional: post a summary to Linear

Only after the user confirms:

- Post a comment on the issue (`save_comment`) with what was implemented, the branch and PR link, and how it was verified — trimmed to what teammates need.
- Do **not** change the issue's state, assignee, or labels, even if the work is finished. That's the user's call to make in Linear.

## Step 11 — Offer to merge into main

After everything else, ask whether the user wants the task branch merged into `main` and pushed. Never merge or push to `main` without their explicit yes in this conversation.

- If the status was **Partial** or **Blocked**, still ask — but restate what's missing in the question so the user decides with eyes open.
- Prefer merging through the PR so GitHub records it correctly:

  ```bash
  gh pr merge PR_NUMBER
  ```

- Only when there is no PR, or the user asks for that path:

  ```bash
  git checkout main
  git merge TASK_BRANCH
  git push
  ```

- The branch already contains latest `main` from Step 3, so this should be conflict-free. If it conflicts, abort and report — never resolve conflicts silently on `main`.
- Confirm with `git log -1 --oneline` and `git status`, and report what was merged and pushed (include the PR URL when merged via PR).
- Do not delete the task branch unless the user asks.

## Safety checklist

- [ ] Issue and all its comments read before any code was written
- [ ] Current repo verified to match the task's project — stopped on mismatch instead of building the wrong thing
- [ ] Checked whether the task was already implemented before re-implementing it
- [ ] Working tree was clean (or the user decided) before switching branches
- [ ] All work done on the task branch, created from up-to-date `main` — nothing committed to `main`
- [ ] Existing branch/PR for the issue continued, not duplicated with a second branch
- [ ] Plan shown to the user before editing; ambiguities raised rather than guessed
- [ ] Non-code tasks answered with a required-actions summary, not forced into code
- [ ] Only files belonging to this task changed and staged
- [ ] Database changes: model ↔ migration ↔ task agree, and every consumer updated
- [ ] Tests/build/lint actually run, results reported honestly including failures
- [ ] Every requirement confirmed with `file:line` evidence before claiming Complete
- [ ] Nothing pushed, no PR opened, nothing posted to Linear without explicit confirmation
- [ ] Issue state/assignee/labels left untouched
- [ ] Merge into `main` + push only after the user's explicit yes, through the task branch or its PR
