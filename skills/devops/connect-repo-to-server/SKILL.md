---
name: connect-repo-to-server
description: Interactively connect a server to a private GitHub repo using a per-repo deploy key, then clone it. Use when the user wants to deploy/clone a private GitHub repository onto a server, set up a deploy key, or give a server read access to a repo. The skill asks for the project name and how to reach the server (pem file or ssh command), runs all server-side steps over SSH, and hands the user the exact text to paste into GitHub.
---

# Connect a Repo to a Server

Walk the user through giving a server read access to one private GitHub repo via a **deploy key** (an SSH key scoped to a single repo), then clone it. You run every server-side command over SSH yourself. The only manual step is pasting the public key into GitHub's web UI — you cannot automate that, so make it copy-paste simple.

Keep it conversational and simple. Ask for what you need, then do the work. Show the user only what they have to act on.

## Step 1 — Gather inputs

Ask the user for these (ask for any you don't already have; accept them in any order):

- **Project / repo name** → `REPO_NAME` (short, e.g. `example-api`). Used for the key filename, SSH host alias, and default app directory.
- **GitHub repo** → the SSH clone URL `git@github.com:GH_USER/REPO_NAME.git`, or just `GH_USER/REPO_NAME`. Derive `GH_USER` and `REPO_NAME` from it.
- **How to reach the server** — one of:
  - a **pem / key file path** plus `user@host` (e.g. `~/keys/box.pem` + `deploy@1.2.3.4`), or
  - a full **ssh command / host alias** they already use (e.g. `ssh my-server`).
- **Where the code should live** → `APP_DIR` (default to `/home/REPO_NAME` if they don't care).

From the connection info, build a reusable SSH prefix:
- pem file → `ssh -i <PEM_PATH> <user@host>`
- ssh command / alias → use it as given (strip a trailing `ssh` only if needed to append remote commands)

Call it `SSH` below. Every remote command is run as `<SSH> '<command>'`. Confirm the connection works before doing anything else:

```bash
<SSH> 'echo connected as $(whoami) on $(hostname)'
```

If that fails, stop and help fix the connection (wrong path, perms on the pem file `chmod 600`, wrong user/host, port) before continuing.

## Step 2 — Make sure git is installed

```bash
<SSH> 'command -v git || (sudo apt update && sudo apt install -y git)'
<SSH> 'git --version'
```

## Step 3 — Generate the deploy key on the server

The private key must be generated **on the server** and never leaves it. One key per repo — never reuse.

```bash
<SSH> 'ssh-keygen -t ed25519 -N "" -f ~/.ssh/deploy_REPO_NAME -C "deploy@REPO_NAME"'
<SSH> 'chmod 600 ~/.ssh/deploy_REPO_NAME && chmod 644 ~/.ssh/deploy_REPO_NAME.pub'
```

If `~/.ssh/deploy_REPO_NAME` already exists, ask whether to reuse it or overwrite (overwriting means re-pasting on GitHub).

## Step 4 — Hand the user the GitHub paste step

Print the public key:

```bash
<SSH> 'cat ~/.ssh/deploy_REPO_NAME.pub'
```

Then give the user **exactly** this to do, with the key inlined so they can copy it:

> 1. Open **https://github.com/GH_USER/REPO_NAME/settings/keys**
> 2. Click **Add deploy key**
> 3. **Title:** `<something identifying the server>`
> 4. **Key:** paste this:
>    ```
>    ssh-ed25519 AAAA... deploy@REPO_NAME
>    ```
> 5. Leave **Allow write access** unchecked (the server only needs to pull).
> 6. Click **Add key**.

Then **wait** — ask the user to confirm they've added it before continuing. Do not proceed until they say yes.

## Step 5 — Configure SSH on the server to use this key for this repo

GitHub serves every repo from `github.com`, so define a host alias that maps to the deploy key:

```bash
<SSH> 'grep -q "Host github-REPO_NAME" ~/.ssh/config 2>/dev/null || printf "\nHost github-REPO_NAME\n    HostName github.com\n    User git\n    IdentityFile ~/.ssh/deploy_REPO_NAME\n    IdentitiesOnly yes\n" >> ~/.ssh/config'
<SSH> 'chmod 600 ~/.ssh/config'
```

Test the alias (auto-accept the host key on first connect):

```bash
<SSH> 'ssh -T -o StrictHostKeyChecking=accept-new git@github-REPO_NAME'
```

Success looks like: `Hi GH_USER/REPO_NAME! You've successfully authenticated...`.
`Permission denied (publickey)` means the deploy key wasn't added on GitHub correctly — send the user back to Step 4.

## Step 6 — Clone the repo (using the alias URL)

The clone URL must use the alias host, not `github.com`:

```bash
<SSH> 'sudo mkdir -p APP_DIR && sudo chown "$(whoami):$(whoami)" APP_DIR'
<SSH> 'git clone git@github-REPO_NAME:GH_USER/REPO_NAME.git APP_DIR'
<SSH> 'git -C APP_DIR log -1 --oneline'
```

The last command should print the latest commit — that confirms it worked.

## Step 7 — Wrap up

Tell the user it's done, and that updating later is just:

```bash
<SSH> 'git -C APP_DIR pull'
```

If they want a different OS user to own/run the app, offer the optional ownership step:

```bash
<SSH> 'sudo chown -R APP_USER:APP_USER APP_DIR'
```

## Notes

- Replace every `REPO_NAME`, `GH_USER`, `APP_DIR`, `APP_USER`, `<SSH>`, `<PEM_PATH>` with the real values before running. Never print literal placeholders to the user.
- Run remote commands one logical step at a time and check each result before moving on — don't chain the whole flow blindly.
- If anything fails, diagnose with the user rather than retrying the same command. Common issues: pem perms (`chmod 600`), wrong clone URL (`github.com` instead of the alias), `Bad owner or permissions on ~/.ssh/config` (`chmod 600`).
- To rotate/revoke later: delete the deploy key in GitHub repo Settings → Deploy keys, then `rm ~/.ssh/deploy_REPO_NAME*` and remove the `Host github-REPO_NAME` block from `~/.ssh/config`.
