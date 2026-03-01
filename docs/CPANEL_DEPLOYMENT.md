# cPanel Git Deployment Guide

> **Complete guide for deploying the MCADV website to cPanel using Git Version Control**

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Authentication Setup](#authentication-setup)
   - [Personal Access Token (HTTPS)](#personal-access-token-https)
   - [SSH Key](#ssh-key)
4. [Setting Up Git Version Control in cPanel](#setting-up-git-version-control-in-cpanel)
5. [Directory Structure & Path Management](#directory-structure--path-management)
6. [Automatic Deployment](#automatic-deployment)
   - [Webhook Setup](#webhook-setup)
   - [Cron Job Setup](#cron-job-setup)
7. [Security Best Practices](#security-best-practices)
8. [Maintenance & Updates](#maintenance--updates)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide explains how to deploy the MCADV website (`website/` subdirectory) to a cPanel-hosted server using cPanel's built-in **Git Version Control** feature. Once configured, pushing changes to GitHub will automatically update your live site.

The MCADV website files live inside the `website/` subdirectory of this repository. This guide covers how to handle that subdirectory correctly when deploying to cPanel.

---

## Prerequisites

- cPanel hosting account with **Git Version Control** enabled (cPanel 66+)
- GitHub repository access
- SSH or HTTPS access to your cPanel account
- Your cPanel **home directory** path (e.g. `/home/yourusername`)

> **Note:** Ask your hosting provider if you are unsure whether Git Version Control is available on your plan.

---

## Authentication Setup

Before cloning from GitHub, you need to authenticate. Choose **one** of the two methods below.

### Personal Access Token (HTTPS)

HTTPS with a Personal Access Token (PAT) is the simplest method and works without SSH key configuration.

#### Step 1 – Generate a GitHub Personal Access Token

1. Go to **GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)**
2. Click **Generate new token (classic)**
3. Set a descriptive name (e.g. `cPanel MCADV Deploy`)
4. Set an expiration that suits your needs (90 days or longer)
5. Select the following scopes:
   - `repo` (Full control of private repositories) — or just `public_repo` if the repository is public
6. Click **Generate token** and **copy the token immediately** (it will not be shown again)

#### Step 2 – Use the Token in cPanel

When cPanel prompts for the clone URL, use this format:

```
https://<github-username>:<personal-access-token>@github.com/hostyorkshire/MCADV.git
```

Replace `<github-username>` with your GitHub username and `<personal-access-token>` with the token you just generated.

> **Warning:** Never share or commit this URL. The token grants write access to your repositories.

---

### SSH Key

SSH is the recommended method for long-term deployments because it does not require token rotation.

#### Step 1 – Generate an SSH Key in cPanel

1. Log in to cPanel
2. Navigate to **Security → SSH Access**
3. Click **Manage SSH Keys**
4. Click **Generate a New Key**
5. Enter a key name (e.g. `github_deploy`)
6. Leave the passphrase blank for automated deployments (or set one for added security)
7. Click **Generate Key**
8. Click **Manage** next to the new key, then **Authorize** it

[Screenshot: cPanel SSH Key Manager showing authorized keys]

#### Step 2 – Add the Public Key to GitHub

1. In cPanel SSH Access, click **View/Download** next to your public key
2. Copy the entire public key content
3. Go to **GitHub → Settings → SSH and GPG keys**
4. Click **New SSH key**
5. Give it a title (e.g. `cPanel Server`)
6. Paste the public key and click **Add SSH key**

#### Step 3 – Use SSH Clone URL

When cPanel prompts for the clone URL, use:

```
git@github.com:hostyorkshire/MCADV.git
```

> **When to use SSH vs HTTPS:**
> - Use **SSH** for long-lived server deployments (no token expiry)
> - Use **HTTPS + PAT** for quick setup or when SSH is blocked by your host

---

## Setting Up Git Version Control in cPanel

### Step 1 – Open Git Version Control

1. Log in to cPanel
2. Search for **Git Version Control** or find it under the **Files** section
3. Click **Create**

[Screenshot: cPanel Git Version Control interface]

### Step 2 – Configure the Repository

Fill in the form:

| Field | Value |
|-------|-------|
| **Clone URL** | `https://github.com/hostyorkshire/MCADV.git` (or SSH URL) |
| **Repository Path** | `/home/<username>/mcadv-repo` (see note below) |
| **Repository Name** | `MCADV` |

> **Important – Repository Path vs Document Root:**  
> Clone the repository to a **non-public** directory (e.g. `/home/<username>/mcadv-repo`), **not** directly into `public_html`. The website files are in the `website/` subdirectory, so you need to point your document root at that subdirectory (see [Directory Structure & Path Management](#directory-structure--path-management)).

### Step 3 – Clone the Repository

Click **Create** and cPanel will clone the repository. This may take a minute depending on repository size.

[Screenshot: cPanel Git Version Control repository list after successful clone]

### Step 4 – Verify the Clone

Connect to your server via **Terminal** (cPanel → Terminal) or SSH, then run:

```bash
ls /home/<username>/mcadv-repo/website/
```

You should see `index.html`, `style.css`, and `dashboard/`.

---

## Directory Structure & Path Management

The MCADV repository structure is:

```
MCADV/                      ← repository root (cloned here)
├── website/                ← website files (this is your document root)
│   ├── index.html
│   ├── style.css
│   └── dashboard/
├── docs/
├── scripts/
└── ...
```

### Option A – Symlink (Recommended)

Create a symlink from your `public_html` to the `website/` subdirectory:

```bash
# Remove or back up existing public_html if needed
mv ~/public_html ~/public_html.bak

# Create symlink pointing public_html at the website subdirectory
ln -s /home/<username>/mcadv-repo/website /home/<username>/public_html
```

After this, any `git pull` to `/home/<username>/mcadv-repo` will automatically update the live site.

### Option B – Adjust the Document Root in cPanel

1. Go to **cPanel → Domains** (or **Addon Domains / Subdomains**)
2. Edit the domain's **Document Root**
3. Set it to: `/home/<username>/mcadv-repo/website`

[Screenshot: cPanel Domains interface showing document root field]

> **Note:** Option A (symlink) is generally simpler to maintain. Option B works well when you cannot modify `public_html` directly.

### Option C – Separate Document Root Directory (Alternative)

If your host does not support symlinks or custom document roots, use the `.cpanel.yml` deployment file to copy files:

Create `.cpanel.yml` in the repository root:

```yaml
---
deployment:
  tasks:
    - export DEPLOYPATH=/home/<username>/public_html/
    - /bin/cp -r website/* $DEPLOYPATH
```

cPanel will run this file automatically on each pull. Replace `<username>` with your actual cPanel username.

> **Note:** `.cpanel.yml` requires cPanel's **Git Version Control** deployment hooks to be enabled. Check with your hosting provider.

---

## Automatic Deployment

### Webhook Setup

GitHub webhooks trigger an automatic `git pull` on your cPanel server whenever you push to GitHub.

#### Step 1 – Find Your cPanel Webhook URL

1. In cPanel, open **Git Version Control**
2. Click **Manage** on your MCADV repository
3. Look for the **Clone URL** section — the webhook URL is shown as **Deployment URL** or similar

The URL typically looks like:

```
https://yourdomain.com/cpanelwebhooks/commit?repository=MCADV&branch=main
```

[Screenshot: cPanel Git Version Control repository management panel showing deployment URL]

> **Note:** The exact location of the webhook URL varies by cPanel version and hosting provider. If you cannot find it, check **cPanel → Git Version Control → Manage → Basic Information**.

#### Step 2 – Add the Webhook in GitHub

1. Go to your GitHub repository: `https://github.com/hostyorkshire/MCADV`
2. Click **Settings → Webhooks → Add webhook**
3. Fill in the form:

| Field | Value |
|-------|-------|
| **Payload URL** | Your cPanel webhook URL |
| **Content type** | `application/json` |
| **Secret** | Generate a strong random string and save it |
| **Which events?** | Select **Just the push event** |
| **Active** | ✅ Checked |

4. Click **Add webhook**

[Screenshot: GitHub webhook configuration form]

#### Step 3 – Verify Webhook Delivery

1. In GitHub, click on your webhook
2. Go to the **Recent Deliveries** tab
3. Make a test push to GitHub
4. Check that the delivery shows a green ✅ with HTTP 200 response

#### Webhook Security Considerations

- Always set a **webhook secret** to verify requests come from GitHub
- Use HTTPS for the webhook URL (never HTTP)
- Your cPanel server should validate the `X-Hub-Signature-256` header if you have a custom deployment script

---

### Cron Job Setup

If webhooks are not available (e.g. your host blocks inbound webhooks), use a cron job to periodically pull updates.

#### Step 1 – Add a Cron Job in cPanel

1. Go to **cPanel → Cron Jobs**
2. Set the schedule (recommended: every 5 minutes)
3. Enter the command:

```bash
cd /home/<username>/mcadv-repo && /usr/bin/git pull origin main >> /home/<username>/logs/deploy.log 2>&1
```

Or use the provided deployment script for better logging:

```bash
/bin/bash /home/<username>/mcadv-repo/scripts/cpanel-deploy.sh >> /home/<username>/logs/deploy.log 2>&1
```

[Screenshot: cPanel Cron Jobs configuration interface]

#### Recommended Cron Intervals

| Interval | Cron Expression | Use Case |
|----------|----------------|----------|
| Every 5 minutes | `*/5 * * * *` | Active development |
| Every 15 minutes | `*/15 * * * *` | Regular updates |
| Every hour | `0 * * * *` | Infrequent changes |
| Daily at midnight | `0 0 * * *` | Stable production |

#### Step 2 – Verify the Cron Job

Check the log file after the first scheduled run:

```bash
cat /home/<username>/logs/deploy.log
```

You should see output similar to:

```
[2024-01-15 02:00:01] Starting deployment...
Already up to date.
[2024-01-15 02:00:02] Deployment complete.
```

---

## Security Best Practices

### 1. Protect the `.git` Directory

The `.git` directory must not be accessible from the web. Add this to your document root's `.htaccess`:

```apache
# Protect .git directory
<DirectoryMatch "^/.*/\.git/">
    Order deny,allow
    Deny from all
</DirectoryMatch>
```

This protection is already included in the root `.htaccess` file of this repository. Verify it is in place after deployment.

### 2. Secure the Webhook Endpoint

- Use a **webhook secret** (see [Webhook Setup](#webhook-setup))
- Ensure HTTPS is enabled on your domain (use Let's Encrypt via cPanel → SSL/TLS)
- Rotate the webhook secret if compromised

### 3. Manage Credentials Safely

- **Never** commit Personal Access Tokens or passwords to the repository
- Store the PAT in the clone URL (cPanel encrypts this internally)
- Regularly rotate your PAT (set a calendar reminder)
- Use SSH keys where possible — they do not expire

### 4. File Permission Recommendations

Run these commands after initial deployment:

```bash
# Directories: 755 (owner can write, others read/execute)
find /home/<username>/mcadv-repo/website -type d -exec chmod 755 {} \;

# Files: 644 (owner can write, others read only)
find /home/<username>/mcadv-repo/website -type f -exec chmod 644 {} \;
```

### 5. Protect Sensitive Repository Files

Add to `website/.htaccess` to prevent access to repository meta-files:

```apache
# Block access to dot-files and dot-directories
<FilesMatch "^\.(git|env|gitignore|htaccess)">
    Order deny,allow
    Deny from all
</FilesMatch>
```

---

## Maintenance & Updates

### Manually Pull Updates

```bash
cd /home/<username>/mcadv-repo
git pull origin main
```

### Switch Branches

```bash
cd /home/<username>/mcadv-repo
git fetch origin
git checkout <branch-name>
```

> **Note:** In cPanel Git Version Control, you can also change the branch via **Manage → Branch**.

### Rollback a Deployment

To roll back to a previous commit:

```bash
cd /home/<username>/mcadv-repo

# View recent commits
git log --oneline -10

# Reset to a specific commit (replace <commit-hash>)
git reset --hard <commit-hash>
```

> **Warning:** `git reset --hard` discards all local changes. Only use this when you want to roll back completely.

### Update Git Configuration

```bash
# Set your identity (required for some git operations)
git config user.email "deploy@yourdomain.com"
git config user.name "cPanel Deploy"

# Verify remote URL
git remote -v

# Update remote URL (e.g. when rotating a PAT)
git remote set-url origin https://<username>:<new-token>@github.com/hostyorkshire/MCADV.git
```

### Checking Deployment Logs in cPanel

- **Git Version Control logs:** cPanel → Git Version Control → Manage → Deployment Log
- **Cron job logs:** `/home/<username>/logs/deploy.log` (if using the provided script)
- **Web server error logs:** cPanel → Metrics → Errors

---

## Troubleshooting

### Permission Errors

**Symptom:** `fatal: could not create work tree dir` or `permission denied`

**Solution:**
```bash
# Check ownership of the repository directory
ls -la /home/<username>/

# Fix ownership if needed (run as root or contact your host)
chown -R <username>:<username> /home/<username>/mcadv-repo
```

---

### Authentication Failures

**Symptom:** `Authentication failed` or `Repository not found`

**Solutions:**
- Verify your PAT has not expired (GitHub → Settings → Developer settings → Tokens)
- Check the clone URL includes the correct username and token
- For SSH: verify the public key is added to GitHub and authorized in cPanel

```bash
# Test SSH connection to GitHub
ssh -T git@github.com
# Expected: "Hi <username>! You've successfully authenticated..."
```

---

### Webhook Not Triggering

**Symptom:** Pushing to GitHub does not update the site

**Solutions:**
1. Check GitHub webhook delivery logs (GitHub → repo → Settings → Webhooks → Recent Deliveries)
2. Verify the webhook URL is correct and accessible from the internet
3. Check cPanel firewall rules — port 443 must be open inbound
4. Try manually triggering the webhook from GitHub (click "Redeliver")

---

### File Path Issues

**Symptom:** 404 errors or wrong files served

**Solutions:**
1. Verify the document root points to `website/` (not the repo root)
2. Check the symlink is valid: `ls -la ~/public_html`
3. Confirm `index.html` is present: `ls ~/public_html/`

---

### Git Conflicts

**Symptom:** `git pull` fails with merge conflict errors

**Solution:**
```bash
cd /home/<username>/mcadv-repo

# Discard local changes and force-sync with remote
git fetch origin
git reset --hard origin/main
```

> **Warning:** This discards any local modifications. Only use this if you do not make edits directly on the server.

---

### Checking Deployment Logs

```bash
# View the last 50 lines of the deployment log
tail -50 /home/<username>/logs/deploy.log

# View cPanel Git deployment log (path may vary)
cat ~/.cpanel/logs/git_deploy.log

# Check web server error log
tail -100 /home/<username>/logs/error_log
```

---

*For webhook-specific troubleshooting, see [docs/GITHUB_WEBHOOK_SETUP.md](GITHUB_WEBHOOK_SETUP.md).*  
*For a quick reference checklist, see [docs/QUICK_START_CPANEL.md](QUICK_START_CPANEL.md).*
