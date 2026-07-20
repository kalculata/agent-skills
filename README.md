# DevOps Notebook

A personal collection of [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills) for DevOps work. Each skill is a reusable, step-by-step playbook that Claude can follow — setting up servers, wiring deploys, git workflows — so the know-how is captured once and executed consistently every time.

## Skills

Skills live under `skills/`, grouped by category. Each folder holds one skill as a `SKILL.md` file.

| Category | Skill | What it does |
| --- | --- | --- |
| `devops` | [connect-repo-to-server](./skills/devops/connect-repo-to-server/SKILL.md) | Connect a server to a private GitHub repo via a per-repo deploy key, then clone it. Runs all server-side steps over SSH; the only manual step is pasting the key into GitHub. |
| `git` | [github-commit](./skills/git/github-commit/SKILL.md) | Stage and commit changes with a message that matches the repo's existing commit style. No co-author trailers, no pushes unless asked. |

## Structure

```
skills/
├── devops/
│   └── connect-repo-to-server/
│       └── SKILL.md
└── git/
    └── github-commit/
        └── SKILL.md
```

## Using a skill

Point Claude Code at this repo (or copy a skill folder into your project's `.claude/skills/` or `~/.claude/skills/`), and Claude will pick it up automatically when a task matches the skill's description — or invoke it directly with `/<skill-name>`.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how skills are organized and what a good skill looks like.
