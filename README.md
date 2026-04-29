# DevOps Notebook

A personal notebook of DevOps recipes and runbooks. Each Markdown file documents how to do a specific task, step by step, so I don't have to re-figure it out next time.

## Contents

- [setup-new-server.md](./setup-new-server.md) — Initial setup and hardening for a fresh Linux server (updates, non-root user, SSH key auth, firewall, fail2ban, etc.)

## Conventions

- One topic per file, named with kebab-case (e.g. `setup-new-server.md`).
- Commands are shown in fenced code blocks. Anything the reader must replace is written in `ALL_CAPS` (e.g. `NEW_USER`, `SERVER_IP`).
- Steps that run on the local machine vs. the remote server are labelled `# local` and `# remote`.
- When a command needs `sudo`, it is shown explicitly. The runbooks assume Ubuntu/Debian unless stated otherwise.
