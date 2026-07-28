# Agent Skills

A personal collection of [agent skills](https://docs.claude.com/en/docs/claude-code/skills). Each skill is a reusable, step-by-step playbook that an AI agent can follow — setting up servers, wiring deploys, git workflows — so the know-how is captured once and executed consistently every time.

## Skills

Skills live under `skills/`, grouped by category. Each folder holds one skill as a `SKILL.md` file.

| Category | Skill | What it does |
| --- | --- | --- |
| `development` | [implement-linear-task](./skills/development/implement-linear-task/SKILL.md) | Implement a Linear task end to end: fetch the issue and comments via the Linear MCP server, build a requirement checklist, verify the current repo matches the task's project, check whether the work already exists on main, then create or resume the task branch (Linear's own `gitBranchName`) off up-to-date main and write the code there — never on main. Agrees a plan first, follows the repo's conventions, treats database changes as high-risk, and verifies with the repo's own tests/build/lint before committing. Non-code tasks get a required-actions summary instead. Ends with a Complete/Partial/Blocked report; can push + open a PR, post a summary to Linear, and merge into main, each after confirmation. |
| `development` | [review-linear-task](./skills/development/review-linear-task/SKILL.md) | Review the implementation of a Linear task: fetch the issue and comments via the Linear MCP server, build a requirement checklist, verify the current repo matches the task's project (stopping to help locate the right one on a mismatch), check out the task branch and merge local main into it, verify the task isn't already implemented on main (offering to `gh pr close` a redundant PR if it is), then review the changes for completeness, correctness, scope, regressions, and tests — with extra scrutiny on database/schema changes. Non-code tasks get a required-actions summary from the comments instead. Ends with a Complete/Incomplete/Needs-changes verdict; can post the review to Linear and merge the branch into main + push, each after confirmation. |
| `devops` | [setup-new-server](./skills/devops/setup-new-server/SKILL.md) | Harden a fresh Ubuntu/Debian VPS: non-root sudo user, SSH key auth, non-standard SSH port, UFW, fail2ban, unattended upgrades, and basic sysctl hardening. |
| `devops` | [connect-repo-to-server](./skills/devops/connect-repo-to-server/SKILL.md) | Connect a server to a private GitHub repo via a per-repo deploy key, then clone it. Runs all server-side steps over SSH; the only manual step is pasting the key into GitHub. |
| `git` | [github-commit](./skills/git/github-commit/SKILL.md) | Stage and commit changes with a message that matches the repo's existing commit style. No co-author trailers, no pushes unless asked. |
| `security` | [webapp-security-audit](./skills/security/webapp-security-audit/SKILL.md) | Audit a webapp repo: vulnerable/outdated dependencies, secrets in the working tree and git history (with history-rewrite proposal), and common hardening issues. Ends with a Critical/Medium/Small report saying how to fix each issue and who can fix it. |
| `security` | [mobileapp-security-audit](./skills/security/mobileapp-security-audit/SKILL.md) | Audit a mobile app repo (Flutter-first): vulnerable/outdated dependencies, leaked keystores and API keys in the working tree, bundled assets and git history, plus mobile hardening (insecure storage, cleartext traffic, disabled TLS checks, debuggable builds, missing obfuscation) and a Dart source review for injection, crypto misuse, and client-side-only authorization. Same Critical/Medium/Small report format. |

## Structure

```
skills/
├── development/
│   ├── implement-linear-task/
│   │   └── SKILL.md
│   └── review-linear-task/
│       └── SKILL.md
├── devops/
│   ├── setup-new-server/
│   │   └── SKILL.md
│   └── connect-repo-to-server/
│       └── SKILL.md
├── git/
│   └── github-commit/
│       └── SKILL.md
└── security/
    ├── webapp-security-audit/
    │   └── SKILL.md
    └── mobileapp-security-audit/
        └── SKILL.md
```

## Using a skill

Point your agent at this repo, or copy a skill folder into wherever it looks for skills (e.g. `.claude/skills/` or `~/.claude/skills/` for Claude Code). The agent picks a skill up automatically when a task matches its description — in Claude Code you can also invoke one directly with `/<skill-name>`.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how skills are organized and what a good skill looks like.
