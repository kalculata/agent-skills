# Contributing

## Organization

Skills are organized **by folder**: each top-level folder under `skills/` is a category, and each category contains related skills.

```
skills/
└── <category>/          # a group of related skills (e.g. devops, git)
    └── <skill-name>/    # one folder per skill, kebab-case
        └── SKILL.md     # the skill itself
```

- **Group related skills together.** Server provisioning and deploy-key setup belong in `devops/`; commit and branching helpers belong in `git/`. If a new skill doesn't fit an existing category, create a new folder for it.
- **One skill per folder.** The folder name is the skill name, in kebab-case (e.g. `connect-repo-to-server`). Supporting files (scripts, templates, references) live alongside `SKILL.md` in the same folder.

## Writing a skill

Every `SKILL.md` starts with YAML frontmatter:

```yaml
---
name: skill-name            # matches the folder name
description: >-
  What the skill does and when to use it. This is what Claude reads
  to decide whether the skill applies, so include trigger phrases
  ("Use when the user asks to ...").
---
```

Guidelines for the body:

- Write instructions **for Claude to execute**, step by step, in the order the work happens.
- Anything the reader must replace is written in `ALL_CAPS` (e.g. `NEW_USER`, `SERVER_IP`).
- Commands go in fenced code blocks. Label where they run (`# local` vs `# remote`) when it matters.
- State safety rules explicitly (what to never do, what needs user confirmation).
- Assume Ubuntu/Debian for server-side commands unless the skill says otherwise.

## Adding a skill

1. Pick (or create) the right category folder under `skills/`.
2. Create `skills/<category>/<skill-name>/SKILL.md` with frontmatter and instructions.
3. Add the skill to the table in [README.md](./README.md).
