# GitHub Webhook Setup Guide

> Detailed guide for configuring GitHub webhooks to trigger automatic deployments on cPanel.

## Table of Contents

1. [Overview](#overview)
2. [Finding Your cPanel Webhook URL](#finding-your-cpanel-webhook-url)
3. [Configuring the Webhook in GitHub](#configuring-the-webhook-in-github)
4. [Webhook Payload Examples](#webhook-payload-examples)
5. [Testing Webhook Delivery](#testing-webhook-delivery)
6. [Troubleshooting Webhook Issues](#troubleshooting-webhook-issues)

---

## Overview

A GitHub webhook sends an HTTP POST request to your cPanel server whenever you push to the repository. cPanel receives this request and performs a `git pull` to update your deployment.

**Flow:**
```
Developer pushes to GitHub
        │
        ▼
GitHub sends POST to cPanel webhook URL
        │
        ▼
cPanel pulls latest changes from GitHub
        │
        ▼
Live website updated
```

---

## Finding Your cPanel Webhook URL

1. Log in to cPanel
2. Navigate to **Files → Git Version Control**
3. Click **Manage** next to your MCADV repository
4. Look for the **Deployment** section or **Basic Information** panel

The webhook URL will look similar to:

```
https://yourdomain.com:2083/cpanelwebhooks/commit?repository=MCADV
```

Or for some cPanel versions:

```
https://yourdomain.com/cpanelwebhooks/commit?repository=MCADV&branch=main
```

[Screenshot: cPanel Git Version Control management panel with webhook/deployment URL highlighted]

> **Note:** If your cPanel does not show a webhook URL, your hosting provider may not have enabled this feature. Use the [Cron Job method](CPANEL_DEPLOYMENT.md#cron-job-setup) instead.

---

## Configuring the Webhook in GitHub

### Step 1 – Open Webhook Settings

1. Go to `https://github.com/hostyorkshire/MCADV`
2. Click **Settings** (top navigation)
3. Click **Webhooks** in the left sidebar
4. Click **Add webhook**

[Screenshot: GitHub repository Settings → Webhooks page]

### Step 2 – Fill in Webhook Configuration

| Field | Value | Notes |
|-------|-------|-------|
| **Payload URL** | Your cPanel webhook URL | Must be HTTPS |
| **Content type** | `application/json` | Required by most cPanel versions |
| **Secret** | A strong random string | Used to verify authenticity |
| **SSL verification** | Enable SSL verification | Requires valid SSL certificate |
| **Which events?** | Just the push event | Triggers on every push |
| **Active** | ✅ Checked | Webhook is live immediately |

#### Generating a Webhook Secret

Use a strong random string. You can generate one with:

```bash
# On Linux/Mac
openssl rand -hex 32

# On Windows PowerShell
[System.Web.Security.Membership]::GeneratePassword(32, 5)
```

Save this secret — you'll need it if you implement server-side signature verification.

### Step 3 – Save the Webhook

Click **Add webhook**. GitHub will immediately send a ping event to verify the URL is reachable.

[Screenshot: Completed GitHub webhook configuration form]

---

## Webhook Payload Examples

### Push Event Payload (Simplified)

When you push to the `main` branch, GitHub sends a payload like this:

```json
{
  "ref": "refs/heads/main",
  "before": "abc123",
  "after": "def456",
  "repository": {
    "id": 123456789,
    "name": "MCADV",
    "full_name": "hostyorkshire/MCADV",
    "html_url": "https://github.com/hostyorkshire/MCADV"
  },
  "pusher": {
    "name": "yourusername",
    "email": "you@example.com"
  },
  "commits": [
    {
      "id": "def456...",
      "message": "Update website styles",
      "timestamp": "2024-01-15T10:00:00Z",
      "author": {
        "name": "Your Name",
        "email": "you@example.com"
      },
      "added": ["website/new-page.html"],
      "modified": ["website/style.css"],
      "removed": []
    }
  ]
}
```

### Ping Event Payload

Sent when the webhook is first created:

```json
{
  "zen": "Speak like a human.",
  "hook_id": 12345678,
  "hook": {
    "type": "Repository",
    "id": 12345678,
    "events": ["push"],
    "active": true,
    "config": {
      "content_type": "json",
      "url": "https://yourdomain.com/cpanelwebhooks/commit"
    }
  }
}
```

A successful ping returns HTTP 200.

---

## Testing Webhook Delivery

### Test via GitHub UI

1. Go to **GitHub → repo → Settings → Webhooks**
2. Click on your webhook
3. Scroll to **Recent Deliveries**
4. Click the latest delivery (or the ping delivery)
5. Check:
   - **Response code:** Should be `200`
   - **Response body:** Should confirm success

[Screenshot: GitHub webhook Recent Deliveries panel with successful 200 response]

### Test by Making a Push

1. Make a small, harmless change (e.g. add a blank line to `website/README.md`)
2. Commit and push:
   ```bash
   git add website/README.md
   git commit -m "Test webhook deployment"
   git push origin main
   ```
3. Check GitHub webhook deliveries for a `200` response
4. SSH into cPanel and verify the change arrived:
   ```bash
   cd /home/<username>/mcadv-repo
   git log --oneline -3
   ```

### Manual Redeliver

If a delivery failed, you can resend it from GitHub:

1. GitHub → repo → Settings → Webhooks → click webhook
2. Recent Deliveries → click a failed delivery
3. Click **Redeliver**

---

## Troubleshooting Webhook Issues

### HTTP 404 – Webhook URL Not Found

**Cause:** Incorrect webhook URL or cPanel endpoint not available.

**Solutions:**
- Double-check the URL from cPanel Git Version Control
- Ensure the repository name in the URL matches exactly (case-sensitive)
- Contact your hosting provider to confirm webhooks are enabled

---

### HTTP 500 – Internal Server Error

**Cause:** cPanel encountered an error executing the `git pull`.

**Solutions:**
```bash
# SSH into cPanel and check git status
cd /home/<username>/mcadv-repo
git status

# Look for conflicts or detached HEAD state
git log --oneline -5

# If in conflict, reset to remote
git fetch origin
git reset --hard origin/main
```

---

### Connection Refused / Timeout

**Cause:** cPanel server firewall is blocking inbound connections.

**Solutions:**
- Verify port 443 (HTTPS) is open inbound on your cPanel server
- Ask your hosting provider to whitelist GitHub webhook IP ranges
- GitHub's webhook IPs can be found at: `https://api.github.com/meta` (look for `hooks` key)

---

### Webhook Triggers But Site Does Not Update

**Cause:** cPanel pulls the code but the document root is not pointing at the correct subdirectory.

**Solutions:**
1. Verify symlink: `ls -la ~/public_html`
2. Verify document root: cPanel → Domains → check document root path
3. Check `.cpanel.yml` if using deployment tasks

---

### Signature Verification Fails

**Cause:** The webhook secret in GitHub does not match the one expected by cPanel.

**Solution:**
- Remove and re-add the webhook secret in both GitHub and your deploy script
- Ensure there are no leading/trailing spaces in the secret

---

### Too Many Deliveries / Rate Limiting

GitHub webhooks are rate-limited per repository. For very frequent pushes, consider:
- Debouncing deployments in your deploy script
- Using a cron job instead (see [Cron Job Setup](CPANEL_DEPLOYMENT.md#cron-job-setup))

---

*See [docs/CPANEL_DEPLOYMENT.md](CPANEL_DEPLOYMENT.md) for the full deployment guide.*
