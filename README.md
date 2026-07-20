# Agent Skills

A personal collection of [agent skills](https://docs.claude.com/en/docs/claude-code/skills). Each skill is a reusable, step-by-step playbook that an AI agent can follow — setting up servers, wiring deploys, git workflows — so the know-how is captured once and executed consistently every time.

## Skills

Skills live under `skills/`, grouped by category. Each folder holds one skill as a `SKILL.md` file.

| Category | Skill | What it does |
| --- | --- | --- |
| `devops` | [connect-repo-to-server](./skills/devops/connect-repo-to-server/SKILL.md) | Connect a server to a private GitHub repo via a per-repo deploy key, then clone it. Runs all server-side steps over SSH; the only manual step is pasting the key into GitHub. |
| `git` | [github-commit](./skills/git/github-commit/SKILL.md) | Stage and commit changes with a message that matches the repo's existing commit style. No co-author trailers, no pushes unless asked. |
| `security` | [webapp-security-audit](./skills/security/webapp-security-audit/SKILL.md) | Audit a webapp repo: vulnerable/outdated dependencies, secrets in the working tree and git history (with history-rewrite proposal), and common hardening issues. Ends with a Critical/Medium/Small report saying how to fix each issue and who can fix it. |

## Structure

```
skills/
├── devops/
│   └── connect-repo-to-server/
│       └── SKILL.md
├── git/
│   └── github-commit/
│       └── SKILL.md
└── security/
    └── webapp-security-audit/
        └── SKILL.md
```

## Using a skill

Point your agent at this repo, or copy a skill folder into wherever it looks for skills (e.g. `.claude/skills/` or `~/.claude/skills/` for Claude Code). The agent picks a skill up automatically when a task matches its description — in Claude Code you can also invoke one directly with `/<skill-name>`.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how skills are organized and what a good skill looks like.
