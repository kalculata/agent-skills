---
name: github-commit
description: >-
  Stage and commit git changes with messages that match the repo's style.
  Use when the user asks to commit, create a git commit, stage and commit,
  or write a commit message for current changes.
---

# GitHub Commit

Create a clean commit only when the user explicitly asks. Inspect changes first, stage the right files, then commit with a message that matches this repository's history.

## Before you start

- Do **not** commit unless the user asked for it in this turn (or a user rule requires it).
- Do **not** push unless the user explicitly asks.
- Never update git config, skip hooks, force-push, or run destructive git commands unless explicitly requested.
- **No co-authors** — commit as the user only. Never append `Co-Authored-By`, `Signed-off-by`, or similar trailers for Cursor, Claude Code, Copilot, or any AI tool. Do not pass `--author` or `--trailer` flags to add them.

## Step 1 — Read the current state

Run these **in parallel** with the Shell tool:

```bash
git status
```

```bash
git diff && git diff --staged
```

```bash
git log -15 --oneline
```

From the output, determine:

1. **Untracked files** — new files not yet in git.
2. **Modified / deleted files** — unstaged or already staged.
3. **Repo commit style** — read `git log` and mirror it (this repo often uses short imperative lines like `Add setup-new-server`; other repos may use Conventional Commits like `feat(scope): summary`).

If there is nothing to commit (no untracked files and no modifications), stop and tell the user.

## Step 2 — Decide what to stage

- Stage only files that belong to the user's request.
- **Never** stage files that likely contain secrets (`.env`, `credentials.json`, `*.pem`, private keys, tokens). Warn the user if they asked to commit those.
- If the user said "commit everything" or did not specify files, stage all relevant changes for the task at hand.
- If scope is unclear, ask before staging unrelated files.

```bash
git add <paths>
```

Use explicit paths when possible instead of blind `git add .` unless the user wants everything.

## Step 3 — Draft the commit message

Write a **1–2 sentence** message focused on **why**, not a file list.

### Match the repo first

Follow patterns from `git log`:

| Repo pattern | Example |
|--------------|---------|
| Simple imperative (common here) | `Add connect-repo-to-server skill` |
| Conventional Commits | `feat(deploy): add deploy key runbook` |
| Prefix + scope | `docs: document server hardening steps` |

When unsure, prefer the dominant style in recent history over inventing a new format.

### Message rules

- **Subject**: one line, ≤72 characters, imperative mood (`Add`, `Fix`, `Update`, not `Added` / `Adds`).
- **Body** (optional): only when the change needs context — wrap at ~72 chars, blank line after subject.
- Use accurate verbs: `add` = new capability/file, `update` = enhance existing, `fix` = bug fix, `docs` = documentation only, `refactor` = behavior-preserving restructure.
- Do not mention tool names ("Cursor", "Claude", "AI") or meta noise ("WIP", "misc changes").
- **No co-author lines** — the message is subject (+ optional body) only. Never add:
  ```
  Co-Authored-By: Cursor <...>
  Co-Authored-By: Claude Code <...>
  ```

### Examples for this notebook repo

```
Add connect-repo-to-server skill
```

```
Update deploy-repo-to-server runbook for Ubuntu 24.04
```

```
Fix typo in setup-new-server SSH key instructions
```

## Step 4 — Commit

Use a plain `git commit` with `-m` only. No `--trailer`, no `--author`, no co-author footer in the message body.

Pass the message via HEREDOC so formatting is preserved:

```bash
git commit -m "$(cat <<'EOF'
Subject line here.

Optional body when needed.
EOF
)"
```

After committing, confirm the message has no co-author trailers:

```bash
git log -1 --format=%B
```

If a hook or tool injected a `Co-Authored-By` line, amend only when allowed by the user's git rules — otherwise reset and recommit with a clean message.

Then verify:

```bash
git status
```

## Step 5 — Handle hook failures

If the commit is **rejected** by a pre-commit hook:

1. Read the hook output and fix the reported issues.
2. Stage any hook auto-fixes if needed.
3. Create a **new** commit — do **not** amend unless all amend conditions in the user's git rules are met.

## Safety checklist

- [ ] User explicitly requested a commit
- [ ] Reviewed `git status` and `git diff` (staged + unstaged)
- [ ] Message matches recent `git log` style
- [ ] No `Co-Authored-By` or AI tool attribution in the commit
- [ ] No secrets in staged files
- [ ] Only intended files staged
- [ ] `git status` clean after commit (or only expected leftovers reported)

## Optional — push

Only when the user asks:

```bash
git push -u origin HEAD
```

Never force-push to `main` or `master` without an explicit user request and a warning.
