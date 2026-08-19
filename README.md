# Agent Skills

A personal collection of [agent skills](https://docs.claude.com/en/docs/claude-code/skills). Each skill is a reusable, step-by-step playbook that an AI agent can follow — setting up servers, wiring deploys, git workflows — so the know-how is captured once and executed consistently every time.

## Skills

Skills live under `skills/`, grouped by category. Each folder holds one skill as a `SKILL.md` file — see the file itself for the full details of what it does.

| Category | Skill | What it does |
| --- | --- | --- |
| `development` | [implement-linear-task](./skills/development/implement-linear-task/SKILL.md) | Implement a Linear task end to end: fetch the issue, plan, work on the task branch (never main), verify, then commit/PR/report back to Linear after confirmation. |
| `development` | [review-linear-task](./skills/development/review-linear-task/SKILL.md) | Review a Linear task's implementation against its requirements and end with a Complete/Incomplete/Needs-changes verdict; can post the review to Linear and merge after confirmation. |
| `devops` | [setup-new-server](./skills/devops/setup-new-server/SKILL.md) | Harden a fresh Ubuntu/Debian VPS: sudo user, SSH keys and non-standard port, UFW, fail2ban, unattended upgrades, sysctl hardening. |
| `devops` | [connect-repo-to-server](./skills/devops/connect-repo-to-server/SKILL.md) | Give a server access to a private GitHub repo via a per-repo deploy key, then clone it. Only manual step is pasting the key into GitHub. |
| `frontend` | [huzaifa](./skills/frontend/huzaifa/SKILL.md) | Huzaifa's personal UI taste for webapps: big heading + muted subtitle for section titles, and light/dark mode from day one via theme tokens. |
| `general` | [unslop](./skills/general/unslop/SKILL.md) | Remove AI-writing tells from prose using a catalog of 36 patterns, with scope rules and per-format calibration. |
| `git` | [github-commit](./skills/git/github-commit/SKILL.md) | Stage and commit changes with a message matching the repo's existing style. No co-author trailers, no pushes unless asked. |
| `security` | [webapp-security-audit](./skills/security/webapp-security-audit/SKILL.md) | Audit a webapp repo for vulnerable dependencies, leaked secrets (including git history), and hardening issues. Ends with a Critical/Medium/Small report. |
| `security` | [mobileapp-security-audit](./skills/security/mobileapp-security-audit/SKILL.md) | Same audit for mobile apps (Flutter-first), plus mobile hardening checks and a Dart source review. |

## Using a skill

Point your agent at this repo, or copy a skill folder into wherever it looks for skills (e.g. `.claude/skills/` or `~/.claude/skills/` for Claude Code). The agent picks a skill up automatically when a task matches its description — in Claude Code you can also invoke one directly with `/<skill-name>`.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how skills are organized and what a good skill looks like.
