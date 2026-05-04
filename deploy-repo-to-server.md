# Deploy a Private Repo to a Server (via Deploy Key)

Steps to clone a private Git repository onto a server using a **deploy key** — an SSH key added to a single repository, scoped to that repo only, read-only by default, easy to revoke.

This is the recommended approach for production: the server can read **only** this one repo, the key doesn't depend on any individual person's account, and rotating it is one button click.

Replace the placeholders as you go:

- `REPO_NAME`  — short identifier for the repo (e.g. `example-api`)
- `REPO_URL`   — the SSH clone URL from GitHub (e.g. `git@github.com:user/example-api.git`)
- `GH_USER`    — the GitHub user/org owning the repo
- `APP_DIR`    — where the code will live on the server (e.g. `/srv/example-api`)
- `APP_USER`   — the OS user the app should run as (often the same one you SSH with, or a dedicated `www-data` / app user)

---

## 1. Install git on the server

```bash
# remote
sudo apt update
sudo apt install -y git
git --version
```

---

## 2. Pick where the repo will live

Common conventions:

| Path | When to use |
|------|-------------|
| `/srv/APP_NAME`     | Modern default for self-hosted services |
| `/var/www/APP_NAME` | Web apps served by nginx / Apache |
| `/home/USER/APP_NAME` | Personal projects, single-user box |
| `/opt/APP_NAME`     | Third-party software |

For this guide we'll use `APP_DIR=/srv/REPO_NAME`. Adjust as needed.

---

## 3. Generate a deploy key **on the server**

The private key lives on the server. It's specific to this one repo — never reuse a deploy key across repos.

```bash
# remote
ssh-keygen -t ed25519 -N "" -f ~/.ssh/deploy_REPO_NAME -C "deploy@REPO_NAME"
```

Two files are produced:

- `~/.ssh/deploy_REPO_NAME`     — private, stays on this server
- `~/.ssh/deploy_REPO_NAME.pub` — public, paste into GitHub in the next step

`-N ""` skips the passphrase (the deploy key needs to be usable non-interactively, e.g. by cron / CI).

Lock down perms (ssh-keygen does this, but verify):

```bash
# remote
chmod 600 ~/.ssh/deploy_REPO_NAME
chmod 644 ~/.ssh/deploy_REPO_NAME.pub
```

---

## 4. Add the public key as a deploy key on GitHub

Print it:

```bash
# remote
cat ~/.ssh/deploy_REPO_NAME.pub
```

Copy the entire `ssh-ed25519 AAAA... deploy@REPO_NAME` line.

In GitHub:

1. Open the repo → **Settings** → **Deploy keys** → **Add deploy key**
2. **Title:** something identifying the server, e.g. `example-app server`
3. **Key:** paste the public key
4. **Allow write access:** leave **unchecked** unless the server needs to push (most deployments only pull)
5. Click **Add key**

GitLab equivalent: **Settings → Repository → Deploy keys**.
Bitbucket equivalent: **Repository settings → Access keys**.

---

## 5. Configure SSH on the server to use the deploy key for this repo

GitHub serves every repo over the same hostname (`github.com`), so you can't tell SSH "use this key for THIS repo" by URL alone. The fix: define a custom **Host alias** in `~/.ssh/config` that points at github.com but uses your deploy key.

```bash
# remote
nano ~/.ssh/config
```

Append:

```
Host github-REPO_NAME
    HostName github.com
    User git
    IdentityFile ~/.ssh/deploy_REPO_NAME
    IdentitiesOnly yes
```

Lock perms (ssh refuses to use a world-readable config):

```bash
# remote
chmod 600 ~/.ssh/config
```

Test the alias:

```bash
# remote
ssh -T git@github-REPO_NAME
```

First run will prompt to accept `github.com`'s host fingerprint — type `yes`. On success you'll see:

```
Hi GH_USER/REPO_NAME! You've successfully authenticated, but GitHub does not provide shell access.
```

If you see `Permission denied (publickey)`, the deploy key isn't registered correctly on GitHub.

---

## 6. Clone the repo using the alias

The clone URL **must use the alias hostname**, not `github.com`:

| | |
|---|---|
| Original URL  | `git@github.com:GH_USER/REPO_NAME.git` |
| Use this URL  | `git@github-REPO_NAME:GH_USER/REPO_NAME.git` |

```bash
# remote
sudo mkdir -p APP_DIR
sudo chown "$USER:$USER" APP_DIR
git clone git@github-REPO_NAME:GH_USER/REPO_NAME.git APP_DIR
cd APP_DIR
git log -1 --oneline   # sanity check
```

---

## 7. (Optional) Hand ownership to a dedicated app user

If the app runs as a different user (e.g. `www-data`, a dedicated `APP_USER`):

```bash
# remote
sudo useradd --system --shell /usr/sbin/nologin --home APP_DIR APP_USER 2>/dev/null || true
sudo chown -R APP_USER:APP_USER APP_DIR
```

For pulls under that user (since `nologin` users can't run a shell):

```bash
# remote
sudo -u APP_USER git -C APP_DIR pull
```

---

## 8. Updating later

The deploy key stays valid until you remove it. Pulling is just:

```bash
# remote
cd APP_DIR
git pull
```

The first remote operation in a fresh session may need `ssh-add` or just relies on `IdentityFile` in `~/.ssh/config` — the alias from step 5 means it Just Works.

---

## 9. Multiple repos on the same server

Repeat steps 3–6 for each repo, with a **different** `REPO_NAME` each time:

- New keypair: `~/.ssh/deploy_OTHER_REPO`
- New deploy key in the OTHER repo's GitHub settings
- New `Host github-OTHER_REPO` block in `~/.ssh/config`
- Clone via `git@github-OTHER_REPO:GH_USER/OTHER_REPO.git`

Never reuse one deploy key across repos — that defeats the whole point of scoping.

---

## Rotating / revoking a deploy key

If the server is compromised, decommissioned, or you just want to rotate:

1. **GitHub** → repo → **Settings** → **Deploy keys** → delete the entry. Access is revoked the moment you click delete.
2. **Server:**
   ```bash
   # remote
   rm ~/.ssh/deploy_REPO_NAME ~/.ssh/deploy_REPO_NAME.pub
   ```
   Edit `~/.ssh/config` and remove the `Host github-REPO_NAME` block.
3. To rotate: generate a new key (step 3), add the new public key on GitHub, update / no change to `~/.ssh/config` (filename can stay the same — the new key just replaces the old file), then delete the old key from GitHub.

---

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| `Permission denied (publickey)` on `ssh -T git@github-REPO_NAME` | Public key not added on GitHub, or `IdentityFile` path wrong in `~/.ssh/config` |
| `git@github-REPO_NAME: Permission denied` on clone | URL still using `github.com` instead of the alias |
| `Bad owner or permissions on ~/.ssh/config` | `chmod 600 ~/.ssh/config` |
| Clone works but `git pull` later fails | Running as a different user — try `sudo -u APP_USER git pull`, or check `~APP_USER/.ssh/` has the same alias config |
| `Host key verification failed` | First-time host key not accepted — re-run `ssh -T git@github-REPO_NAME` and type `yes` |

---

## Final checklist

- [ ] `git` installed
- [ ] Deploy keypair generated **on the server** (not on your laptop)
- [ ] Public key added to the repo's GitHub Deploy keys (write access **off** unless needed)
- [ ] `Host github-REPO_NAME` alias added to `~/.ssh/config`, perms `600`
- [ ] `ssh -T git@github-REPO_NAME` returns the success greeting
- [ ] Repo cloned to `APP_DIR` using the alias URL
- [ ] Ownership set correctly for the user that will run the app
- [ ] `git pull` from `APP_DIR` works without prompts
