---
name: setup-new-server
description: >-
  Bring a fresh Ubuntu/Debian server up and harden it before putting anything on
  it — non-root sudo user, SSH key auth, non-standard SSH port, UFW, fail2ban,
  unattended upgrades, and basic sysctl hardening. Use when the user asks to set
  up a new server, provision a VPS, harden SSH, lock down a fresh box, or
  prepare a server before deploying.
---

# Setup a New Server

Walk the user through hardening a fresh Ubuntu/Debian server. Assumes they have just been given `root` (or a default cloud user with `sudo`) and a public IP. You run remote commands over SSH yourself. Keep it conversational — ask for what you need, then do the work.

**Lockout rule:** never disable password auth, root login, or change the SSH port until key login as `NEW_USER` is confirmed in a *second* terminal. Always keep the original session open as a fallback. Always run `sshd -t` before restarting sshd.

## Step 1 — Gather inputs

Ask for any you don't already have:

- **Server IP** → `SERVER_IP`
- **New username** → `NEW_USER` (e.g. `deploy`)
- **SSH port** → `SSH_PORT` (mandatory non-standard port in the high range, e.g. `49222` — do **not** keep `22`)
- **Hostname** (optional) → default `my-server`
- **How to reach it initially** — usually `ssh root@SERVER_IP`, or a cloud default user with sudo

Build an SSH prefix for the initial session (`SSH_ROOT`, e.g. `ssh root@SERVER_IP`). After the new user exists and key auth works, switch to `SSH` as `ssh -i ~/.ssh/id_ed25519_NEW_USER -p SSH_PORT NEW_USER@SERVER_IP` (or the host alias from Step 3c).

Confirm the initial connection:

```bash
# local
<SSH_ROOT> 'echo connected as $(whoami) on $(hostname)'
```

## Step 2 — Update the system

```bash
# remote
apt update && apt upgrade -y
apt dist-upgrade -y
apt autoremove -y
```

Reboot if a kernel was upgraded, then reconnect:

```bash
# remote
[ -f /var/run/reboot-required ] && reboot
```

```bash
# remote
timedatectl set-timezone UTC
hostnamectl set-hostname HOSTNAME
```

## Step 3 — Create a non-root sudo user

Never use `root` for daily work.

```bash
# remote
adduser NEW_USER             # will prompt for a strong password — have the user set it
usermod -aG sudo NEW_USER
id NEW_USER
groups NEW_USER
```

If `adduser` prompts interactively and you cannot drive the prompt, ask the user to run that one command in their own SSH session and confirm when done.

## Step 4 — SSH key auth for the new user

### 4a. Local key (if they don't already have one)

```bash
# local
ssh-keygen -t ed25519 -C "you@example.com" -f ~/.ssh/id_ed25519_NEW_USER
```

Have the user set a strong passphrase. Private key never leaves their machine.

### 4b. Copy the public key

```bash
# local
ssh-copy-id -i ~/.ssh/id_ed25519_NEW_USER.pub NEW_USER@SERVER_IP
```

Manual fallback:

```bash
# remote, as NEW_USER (or as root writing into /home/NEW_USER)
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "PASTE_PUBLIC_KEY_CONTENTS_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
# if done as root:
chown -R NEW_USER:NEW_USER /home/NEW_USER/.ssh
```

### 4c. Test key login — BEFORE hardening SSH

Keep the root session open. In a **new** terminal:

```bash
# local
ssh -i ~/.ssh/id_ed25519_NEW_USER NEW_USER@SERVER_IP
```

**Stop here if this fails.** Do not continue until key login works.

Optional local host alias (`~/.ssh/config`):

```
Host my-server
    HostName SERVER_IP
    User NEW_USER
    IdentityFile ~/.ssh/id_ed25519_NEW_USER
    IdentitiesOnly yes
    Port SSH_PORT
```

(Use `Port 22` until Step 5/6 switch the daemon; then update to `SSH_PORT`.)

## Step 5 — Firewall (UFW) before changing the SSH port

Allow the new port **before** restarting sshd on it.

```bash
# remote
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow SSH_PORT/tcp
# Only if needed:
# sudo ufw allow 80/tcp
# sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Ask whether they need 80/443 before enabling those rules.

## Step 6 — Harden sshd

Prefer a drop-in so package upgrades don't clobber it:

```bash
# remote
sudo tee /etc/ssh/sshd_config.d/99-hardening.conf >/dev/null <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
X11Forwarding no
MaxAuthTries 3
LoginGraceTime 20
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers NEW_USER
Port SSH_PORT
EOF
```

Also check `/etc/ssh/sshd_config` and any other files in `sshd_config.d/` for conflicting `PasswordAuthentication yes` / `Port 22` / `PermitRootLogin` that would override the drop-in (later files win depending on include order — fix conflicts explicitly).

Validate, then restart — **keep the old session open**:

```bash
# remote
sudo sshd -t
sudo systemctl restart ssh
```

From a new terminal, confirm key login on the new port:

```bash
# local
ssh -i ~/.ssh/id_ed25519_NEW_USER -p SSH_PORT NEW_USER@SERVER_IP
```

Confirm password auth is refused:

```bash
# local
ssh -p SSH_PORT -o PreferredAuthentications=password -o PubkeyAuthentication=no NEW_USER@SERVER_IP
# Expected: Permission denied (publickey).
```

Only after both succeed, close the root session. Update the local `~/.ssh/config` `Port` to `SSH_PORT` if you added an alias.

## Step 7 — Fail2ban

```bash
# remote
sudo apt install -y fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

Ensure the `[sshd]` jail has:

```
enabled  = true
port     = SSH_PORT
maxretry = 5
findtime = 10m
bantime  = 1h
```

```bash
# remote
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

## Step 8 — Unattended security upgrades

```bash
# remote
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
sudo systemctl status unattended-upgrades
cat /etc/apt/apt.conf.d/20auto-upgrades
```

Expect `APT::Periodic::Update-Package-Lists "1";` and `APT::Periodic::Unattended-Upgrade "1";`. If `dpkg-reconfigure` is interactive, guide the user through the prompts (enable automatic updates).

## Step 9 — Extra hardening

```bash
# remote
sudo passwd -l root
chmod 750 /home/NEW_USER
sudo timedatectl set-ntp true
```

Do **not** enable `NOPASSWD` sudo unless the user explicitly asks.

Create `/etc/sysctl.d/99-hardening.conf`:

```
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects   = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.log_martians = 1
net.ipv4.ip_forward = 0
```

```bash
# remote
sudo sysctl --system
```

Optional (ask first):

```bash
# remote
sudo apt install -y lynis rkhunter
sudo lynis audit system
sudo rkhunter --update && sudo rkhunter --check --skip-keypress
```

Optional shared-memory line in `/etc/fstab` (ask first):

```
tmpfs /run/shm tmpfs defaults,noexec,nosuid 0 0
```

## Step 10 — Final checklist

Walk the user through confirming:

- [ ] System updated; rebooted if needed
- [ ] `NEW_USER` exists with sudo
- [ ] SSH key login works for `NEW_USER` on `SSH_PORT`
- [ ] Root login and password auth disabled; `sshd -t` clean
- [ ] UFW enabled; only required ports open
- [ ] Fail2ban watching sshd
- [ ] Unattended upgrades enabled
- [ ] Root password locked
- [ ] SSH private key backed up somewhere safe

Remind them: later deploy work (e.g. cloning a private repo) can use the `connect-repo-to-server` skill over `ssh -p SSH_PORT NEW_USER@SERVER_IP`.

## Recovery notes

If locked out: use the provider's serial/VNC console (or IPMI on bare metal), undo the bad sshd/UFW change, then re-test. This is why Steps 4c and 6 insist on a second-session test and `sshd -t`.

## Notes

- Replace every `SERVER_IP`, `NEW_USER`, `SSH_PORT`, `HOSTNAME`, `<SSH_ROOT>`, `<SSH>` before running. Never print literal placeholders to the user as if they were real values.
- Run one logical step at a time; check results before continuing.
- Assume Ubuntu/Debian (`apt`, `ufw`, `systemctl`). If the box is another distro, stop and adapt with the user rather than inventing package names.
