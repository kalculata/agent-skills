---
name: webapp-security-audit
description: >-
  Run a security audit of a web application repository: check dependency
  versions for known vulnerabilities and propose updates, scan the working
  tree and the full git history for .env files, keys and other secrets
  (proposing a history rewrite if any are found), and review common webapp
  hardening issues. Use when the user asks to audit security, check for
  vulnerabilities, scan for leaked secrets, or harden a website/webapp.
  Ends with a severity-ranked report (Critical/Medium/Small) stating how to
  fix each issue and whether the user must fix it manually or you can fix it.
---

# Webapp Security Audit

Audit the current repository for security issues, then present a single consolidated report. This skill is **analysis first**: do not change anything during the audit. Fixes happen only in Step 6, after the user picks what to fix.

Severity levels used throughout:

- 🔴 **Critical** — exploitable now or secrets exposed (leaked credentials, vulnerable dependency with known exploit, debug mode in production).
- 🟠 **Medium** — weakens security but needs conditions to exploit (outdated major versions, missing security headers, permissive CORS).
- 🟡 **Small** — hygiene and hardening (minor version drift, missing `.gitignore` entries, verbose error pages).

## Step 1 — Identify the stack

Look at the repo root to determine what you're auditing:

- `package.json` (+ lockfile → npm / yarn / pnpm / bun)
- `composer.json` (PHP), `requirements.txt` / `pyproject.toml` (Python), `Gemfile` (Ruby), `go.mod` (Go)
- Framework hints: `next.config.*`, `nuxt.config.*`, `vite.config.*`, `artisan`, `manage.py`, `wp-config.php`, etc.
- Deploy hints: `Dockerfile`, `docker-compose.yml`, `nginx*.conf`, CI workflows in `.github/workflows/`

Note everything found — later steps depend on it. If there is no manifest at all, tell the user and continue with Steps 3–5 only.

## Step 2 — Dependency audit

Run the audit tool(s) matching the stack (only the ones that apply):

```bash
# npm / yarn / pnpm
npm audit --json 2>/dev/null || yarn npm audit --json || pnpm audit --json
npm outdated || yarn outdated || pnpm outdated

# PHP
composer audit
composer outdated --direct

# Python
pip-audit || pip list --outdated

# Ruby
bundle audit check --update

# Go
govulncheck ./...
```

If an audit tool is missing, prefer installing/running it in a throwaway way (`npx`, `pipx run`) over polluting the project. If none can run, fall back to reading the lockfile and flagging packages that are several major versions behind.

Record for the report, per finding: package, installed version, fixed version, CVE/advisory if given. Severity mapping: known CVE with available fix → 🔴 if high/critical advisory, 🟠 if moderate; outdated major version with no known CVE → 🟠; minor/patch drift → 🟡.

Fixability: version bumps are usually **agent-fixable** (`npm audit fix`, bump + reinstall + run the test suite). Major-version upgrades with breaking changes are **manual (or agent-assisted with user approval)** — say so per package.

## Step 3 — Secrets in the working tree

Check what is committed *right now*:

```bash
git ls-files | grep -iE '(^|/)\.env(\..*)?$|\.pem$|\.key$|\.p12$|\.pfx$|credentials|secret|id_rsa'
```

Then grep tracked files for hardcoded credentials (API keys, tokens, passwords, connection strings):

```bash
git grep -nIiE '(api[_-]?key|secret|password|token|authorization)[\"'"'"']?\s*[:=]\s*[\"'"'"'][^\"'"'"']{8,}' -- ':!*.lock' ':!*lock.json'
git grep -nIE 'AKIA[0-9A-Z]{16}|sk_live_|ghp_[A-Za-z0-9]{36}|xox[baprs]-|-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----'
```

Also verify `.gitignore` covers `.env*`, key files, and local config. A tracked `.env` or any live-looking credential in code is 🔴. Missing `.gitignore` entries with no secret actually committed is 🟡 Small.

**Never print secret values** in your output — show file, line, and a redacted form (`sk_live_•••`).

## Step 4 — Secrets in git history

Even if the working tree is clean, secrets may live in old commits:

```bash
# Files ever committed under sensitive names, and the commits that touched them
git log --all --diff-filter=A --name-only --format='commit %h' -- '*.env' '.env.*' '*.pem' '*.key' '*credentials*' '*secret*' | grep -v '^$'

# Content search across all history (can be slow on big repos — warn the user first)
git log --all -p -G'AKIA[0-9A-Z]{16}|sk_live_|ghp_|-----BEGIN .*PRIVATE KEY' --format='commit %h %s' -- . ':!*.lock' | grep -E '^commit|AKIA|sk_live_|ghp_|PRIVATE KEY' | head -50
```

If the repo has a public or shared remote, anything found here is 🔴 regardless of whether it was later deleted — **deletion does not remove it from history**.

When something is found, tell the user two things, in this order:

1. **Rotate first.** The exposed credentials must be treated as compromised and revoked/rotated at the provider *before* any history cleanup. Rewriting history does not un-leak a key. This part is always **manual** — only the user can rotate their credentials.
2. **Propose the history rewrite.** Offer to purge the files/strings from history with `git filter-repo` (preferred) or BFG:

```bash
# example: remove every historical .env
git filter-repo --invert-paths --path .env --path-glob '.env.*'
git push --force --all && git push --force --tags
```

Warn explicitly before doing this: it rewrites every commit hash after the earliest affected commit, requires a **force-push**, breaks open PRs, and every collaborator must re-clone. GitHub also caches old commits — the user should contact GitHub support (or make the repo private temporarily) to fully evict them. **Never run the rewrite or force-push without explicit user confirmation in this conversation.** The rewrite itself is **agent-fixable** once confirmed; rotation stays manual.

## Step 5 — Webapp hardening review

Check whichever of these apply to the stack found in Step 1. Keep it to what you can actually verify in the repo; don't speculate.

- **Debug/production flags** — `APP_DEBUG=true`, `DEBUG=True`, `NODE_ENV` not production in deploy config, Laravel/Django debug pages. 🔴 if it ships to production.
- **Security headers** — look in server/framework config (nginx, helmet, middleware) for `Content-Security-Policy`, `X-Frame-Options`/`frame-ancestors`, `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy`. Missing on a production site → 🟠.
- **CORS** — `Access-Control-Allow-Origin: *` combined with credentials, or reflecting arbitrary origins → 🟠.
- **Cookies / sessions** — session cookies without `Secure`, `HttpOnly`, `SameSite` → 🟠.
- **Auth & secrets management** — secret keys generated per-env vs hardcoded defaults (`APP_KEY`, `SECRET_KEY`, JWT secrets); default admin credentials in seeders → 🔴 if a real default secret is committed.
- **Injection surface** — raw SQL string concatenation, `eval`, `dangerouslySetInnerHTML` / `v-html` with user input, unsanitized file uploads (spot-check, note as "needs review" rather than claiming proof) → 🟠.
- **Transport** — HTTP (not HTTPS) URLs to own APIs, missing HSTS/redirect in server config → 🟠.
- **Docker/CI** — containers running as root, secrets passed as build args or echoed in CI logs, overly broad `GITHUB_TOKEN` permissions → 🟠.
- **Source maps / artifacts** — production builds shipping `.map` files or exposing `/.git` via web root config → 🟡.
- **Rate limiting / lockout** — login endpoints with no throttling middleware visible → 🟡 (flag as recommendation).

## Step 6 — The report

Finish with one consolidated report — this is the deliverable. Format:

1. A one-line verdict (e.g. "12 issues: 2 critical, 6 medium, 4 small").
2. A table, **sorted Critical → Medium → Small**:

| # | Severity | Issue | Where | How to fix | Who fixes it |
|---|----------|-------|-------|------------|--------------|
| 1 | 🔴 Critical | `.env` with live Stripe key in git history | commits `a1b2c3d`… | Rotate key at Stripe, then purge history with `git filter-repo` + force-push | Rotation: **you (manual)** · History rewrite: **me, on your go-ahead** |
| 2 | 🟠 Medium | `express` 4.17.1 → 4.19.2 (CVE-2024-…) | `package.json` | Bump and run tests | **Me** |
| 3 | 🟡 Small | `.gitignore` missing `.env.local` | repo root | Add entry | **Me** |

3. For every issue, "Who fixes it" must be explicit: **me** (agent can do it now), **you (manual)** (credentials rotation, provider dashboards, business decisions), or **me, with your approval** (breaking upgrades, history rewrites, force-pushes).
4. End by asking which of the agent-fixable issues to apply. Apply only what the user picks, one logical change per commit if they want commits, and re-run the relevant check afterwards to confirm the fix.

## Safety rules

- Read-only until the user approves fixes; never auto-run `npm audit fix`, upgrades, `git filter-repo`, or any push during the audit.
- Never force-push or rewrite history without explicit confirmation in this conversation, and always state the consequences (new hashes, re-clones, broken PRs) before asking.
- Never print discovered secret values — redact them.
- Exposed secrets are compromised even after history rewrite: rotation always comes first.
- Audit only repos/sites the user owns or is authorized to assess.
