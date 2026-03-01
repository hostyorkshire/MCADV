# cPanel Deployment Quick Start

> Quick reference checklist for deploying MCADV website to cPanel.  
> For full instructions, see [docs/CPANEL_DEPLOYMENT.md](CPANEL_DEPLOYMENT.md).

---

## Prerequisites Checklist

- [ ] cPanel hosting account with **Git Version Control** enabled
- [ ] GitHub account with access to `hostyorkshire/MCADV`
- [ ] GitHub Personal Access Token **or** SSH key (see [Authentication](CPANEL_DEPLOYMENT.md#authentication-setup))
- [ ] HTTPS/SSL active on your domain

---

## Setup Checklist

### 1. Authentication

**Option A – Personal Access Token (HTTPS):**
- [ ] Generate PAT at GitHub → Settings → Developer Settings → Personal Access Tokens
- [ ] Scope: `repo` (or `public_repo` for public repos)
- [ ] Copy token immediately after generation

**Option B – SSH Key:**
- [ ] Generate key: cPanel → Security → SSH Access → Manage SSH Keys → Generate
- [ ] Authorize the key in cPanel
- [ ] Add public key to GitHub → Settings → SSH and GPG keys

---

### 2. Clone Repository in cPanel

- [ ] Open cPanel → **Git Version Control** → **Create**
- [ ] Enter Clone URL:
  - HTTPS: `https://<user>:<token>@github.com/hostyorkshire/MCADV.git`
  - SSH: `git@github.com:hostyorkshire/MCADV.git`
- [ ] Set Repository Path to a **non-public** directory, e.g. `/home/<username>/mcadv-repo`
- [ ] Click **Create** and wait for clone to complete

---

### 3. Point Document Root at `website/` Subdirectory

**Option A – Symlink (recommended):**
```bash
ln -s /home/<username>/mcadv-repo/website /home/<username>/public_html
```

**Option B – Change document root in cPanel:**
- cPanel → Domains → Edit domain → Document Root → `/home/<username>/mcadv-repo/website`

**Option C – Use `.cpanel.yml` to copy files on deploy:**
```yaml
---
deployment:
  tasks:
    - export DEPLOYPATH=/home/<username>/public_html/
    - /bin/cp -r website/* $DEPLOYPATH
```

- [ ] Chosen method applied and tested

---

### 4. Configure Automatic Deployment

**Option A – GitHub Webhook:**
- [ ] Find webhook URL in cPanel → Git Version Control → Manage
- [ ] Add webhook in GitHub → repo → Settings → Webhooks
- [ ] Set Content-Type: `application/json`
- [ ] Add a webhook secret
- [ ] Test delivery shows HTTP 200

**Option B – Cron Job:**
- [ ] Open cPanel → Cron Jobs
- [ ] Add command:
  ```bash
  cd /home/<username>/mcadv-repo && /usr/bin/git pull origin main >> /home/<username>/logs/deploy.log 2>&1
  ```
- [ ] Set interval (e.g. `*/15 * * * *` for every 15 minutes)

---

### 5. Security

- [ ] Verify `.htaccess` protects `.git` directory (check root `.htaccess`)
- [ ] HTTPS enabled on domain (cPanel → SSL/TLS → Let's Encrypt)
- [ ] Webhook secret configured in both GitHub and your deploy script
- [ ] File permissions set: directories `755`, files `644`

---

### 6. Verify Deployment

- [ ] Visit your domain — MCADV website should display correctly
- [ ] Make a small change, push to GitHub, wait for auto-deploy, verify change appears
- [ ] Check deployment log: `tail -f /home/<username>/logs/deploy.log`

---

## Quick Reference Commands

```bash
# Manual pull
cd /home/<username>/mcadv-repo && git pull origin main

# Check current branch and status
cd /home/<username>/mcadv-repo && git status

# View recent deployment log
tail -50 /home/<username>/logs/deploy.log

# Roll back to previous commit
cd /home/<username>/mcadv-repo && git log --oneline -5
cd /home/<username>/mcadv-repo && git reset --hard <commit-hash>
```

---

## Useful Links

- 📖 [Full cPanel Deployment Guide](CPANEL_DEPLOYMENT.md)
- 🔗 [GitHub Webhook Setup Guide](GITHUB_WEBHOOK_SETUP.md)
- ✅ [Deployment Checklist](DEPLOYMENT_CHECKLIST.md)
- 🔧 [Troubleshooting](CPANEL_DEPLOYMENT.md#troubleshooting)
