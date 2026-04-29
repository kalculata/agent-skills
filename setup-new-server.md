# Setup a New Server (Ubuntu / Debian)

Steps to bring a fresh server up and harden it before putting anything on it. Assumes you have just been given `root` access (or a default cloud user with `sudo`) and a public IP.

Replace the placeholders as you go:

- `SERVER_IP` — the server's public IP
- `NEW_USER` — the non-root user you will create (e.g. `deploy`)
- `SSH_PORT` — a non-standard SSH port to use (mandatory — do **not** keep `22`; pick something in the high range, e.g. `49222`)

---

## 1. Log in as root and update the system

```bash
# local
ssh root@SERVER_IP
```

```bash
# remote
apt update && apt upgrade -y
apt dist-upgrade -y
apt autoremove -y
```

Reboot if a kernel was upgraded:

```bash
# remote
[ -f /var/run/reboot-required ] && reboot
```

Set the timezone and hostname while you are here:

```bash
# remote
timedatectl set-timezone UTC
hostnamectl set-hostname my-server
```

---

## 2. Create a non-root user with sudo

Never use `root` for daily work. Create a normal user and give it `sudo`.

```bash
# remote
adduser NEW_USER             # will prompt for a strong password
usermod -aG sudo NEW_USER
```

Verify:

```bash
# remote
id NEW_USER
groups NEW_USER
```

---

## 3. Set up SSH key authentication for the new user

### 3a. Generate a key on your local machine (if you don't already have one)

Use Ed25519 — small, fast, modern.

```bash
# local
ssh-keygen -t ed25519 -C "you@example.com" -f ~/.ssh/id_ed25519_NEW_USER
```

Set a strong passphrase when prompted. Two files are produced:

- `~/.ssh/id_ed25519_NEW_USER`     — private key, **never share**
- `~/.ssh/id_ed25519_NEW_USER.pub` — public key, safe to copy to servers

### 3b. Copy the public key to the server

Easiest way:

```bash
# local
ssh-copy-id -i ~/.ssh/id_ed25519_NEW_USER.pub NEW_USER@SERVER_IP
```

Manual fallback (if `ssh-copy-id` is unavailable):

```bash
# remote, logged in as NEW_USER
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "PASTE_PUBLIC_KEY_CONTENTS_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3c. Test the key login from a new terminal — BEFORE disabling passwords

```bash
# local (new terminal — keep the root session open as a fallback)
ssh -i ~/.ssh/id_ed25519_NEW_USER NEW_USER@SERVER_IP
```

If this fails, fix it now. Do not move on until key login works.

Optional convenience: add a host alias in `~/.ssh/config`:

```
Host my-server
    HostName SERVER_IP
    User NEW_USER
    IdentityFile ~/.ssh/id_ed25519_NEW_USER
    IdentitiesOnly yes
    Port SSH_PORT
```

Then `ssh my-server` is enough.

---

## 4. Harden the SSH daemon

Edit the SSH config:

```bash
# remote
sudo nano /etc/ssh/sshd_config
```

Set (or uncomment) the following:

```
PermitRootLogin no
PasswordAuthentication no
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
UsePAM yes
PubkeyAuthentication yes
PermitEmptyPasswords no
X11Forwarding no
MaxAuthTries 3
LoginGraceTime 20
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers NEW_USER
Port SSH_PORT
```

Some distros put overrides in `/etc/ssh/sshd_config.d/*.conf` — check there too, otherwise your edits may be overridden.

Validate the config before restarting (a typo will lock you out):

```bash
# remote
sudo sshd -t
```

If `sshd -t` exits silently, it's good. Restart:

```bash
# remote
sudo systemctl restart ssh
```

**Keep the existing root SSH session open.** Open a new terminal and confirm you can still log in as `NEW_USER` with the key. Once confirmed, close root.

Confirm password auth is now refused:

```bash
# local
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no NEW_USER@SERVER_IP
# Expected: "Permission denied (publickey)."
```

---

## 5. Firewall (UFW)

Default-deny inbound, allow only what you need.

```bash
# remote
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow SSH_PORT/tcp
# Web servers — only if needed:
# sudo ufw allow 80/tcp
# sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Allow the new SSH port in UFW **before** restarting sshd, so the firewall doesn't drop your reconnect.

---

## 6. Fail2ban (block brute-force attempts)

```bash
# remote
sudo apt install -y fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
```

Inside `[sshd]` make sure:

```
enabled  = true
port     = SSH_PORT
maxretry = 5
findtime = 10m
bantime  = 1h
```

Then:

```bash
# remote
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

---

## 7. Automatic security updates

```bash
# remote
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Verify it's enabled:

```bash
# remote
sudo systemctl status unattended-upgrades
cat /etc/apt/apt.conf.d/20auto-upgrades
```

You should see `APT::Periodic::Update-Package-Lists "1";` and `APT::Periodic::Unattended-Upgrade "1";`.

---

## 8. Other security hardening

### Disable root password (so it cannot be used at all)

```bash
# remote
sudo passwd -l root
```

### Lock down the new user's home directory

```bash
# remote
chmod 750 /home/NEW_USER
```

### Sudo: require password, log everything

`sudo` already requires a password by default — do **not** use `NOPASSWD` unless you have a specific reason. Sudo activity is logged to `/var/log/auth.log`.

### Shared memory hardening (optional)

Add to `/etc/fstab`:

```
tmpfs /run/shm tmpfs defaults,noexec,nosuid 0 0
```

### Kernel / network sysctls

Create `/etc/sysctl.d/99-hardening.conf`:

```
# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects   = 0

# Drop source-routed packets
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0

# SYN flood protection
net.ipv4.tcp_syncookies = 1

# Log martians
net.ipv4.conf.all.log_martians = 1

# Disable IP forwarding (only enable on routers/gateways)
net.ipv4.ip_forward = 0
```

Apply:

```bash
# remote
sudo sysctl --system
```

### Time sync

```bash
# remote
sudo timedatectl set-ntp true
timedatectl status
```

### Auditing tools (optional but useful)

```bash
# remote
sudo apt install -y lynis rkhunter
sudo lynis audit system           # security audit + recommendations
sudo rkhunter --update && sudo rkhunter --check --skip-keypress
```

---

## 9. Final checklist

- [ ] System fully updated, rebooted if needed
- [ ] Non-root user created with `sudo`
- [ ] SSH key login works for the new user
- [ ] `PermitRootLogin no` and `PasswordAuthentication no` in sshd
- [ ] `sshd -t` passes; SSH restarted; password login refused
- [ ] UFW enabled, only required ports open
- [ ] Fail2ban running and watching `sshd`
- [ ] Unattended security upgrades enabled
- [ ] Root password locked
- [ ] Backup of the SSH private key stored somewhere safe (password manager / encrypted backup)

---

## Recovery notes

If you ever lock yourself out:

- Most cloud providers offer a web-based serial / VNC console — log in as a user that still works (or single-user mode) and undo the change.
- On bare metal, you need physical / IPMI access.
- This is exactly why **step 3c** (test key login first) and **step 4** (`sshd -t`, keep old session open) matter.
