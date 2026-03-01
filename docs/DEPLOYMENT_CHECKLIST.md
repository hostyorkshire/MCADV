# Deployment Checklist

> Use this checklist before and after deploying the MCADV website to cPanel.

---

## Pre-Deployment Checklist

### Code Quality

- [ ] All changes committed and pushed to the `main` branch on GitHub
- [ ] Website displays correctly in a local browser (`open website/index.html`)
- [ ] No broken links or missing assets in `website/`
- [ ] CSS and JavaScript files are valid (no console errors in browser DevTools)

### Repository

- [ ] `website/` directory contains the latest `index.html` and `style.css`
- [ ] `.htaccess` file is present in the repository root with `.git` directory protection
- [ ] No sensitive credentials committed to the repository (`git log --oneline -5`)
- [ ] `VERSION` file updated if this is a new release

### cPanel Environment

- [ ] cPanel account is active and accessible
- [ ] Git Version Control feature is available (cPanel → Files → Git Version Control)
- [ ] SSH or HTTPS authentication is configured (see [Authentication Setup](CPANEL_DEPLOYMENT.md#authentication-setup))
- [ ] Target repository path exists and has correct permissions
- [ ] Document root is correctly set to `website/` subdirectory

### SSL / Security

- [ ] HTTPS/SSL certificate is valid on the domain
- [ ] `.htaccess` protects `.git` directory from web access
- [ ] Webhook secret is configured (if using GitHub webhooks)

---

## Deployment Steps

1. [ ] Log in to cPanel
2. [ ] Navigate to Git Version Control
3. [ ] Click **Pull or Deploy** on the MCADV repository
4. [ ] Wait for deployment to complete
5. [ ] Check for errors in the deployment log

---

## Post-Deployment Verification

### Functional Tests

- [ ] Visit the domain in a browser — website loads without errors
- [ ] Website title and content match the latest version
- [ ] All navigation links work
- [ ] Dashboard page loads (if applicable): `/dashboard/`
- [ ] No 404 errors for CSS or image files
- [ ] Browser DevTools Console shows no JavaScript errors

### Security Verification

- [ ] `.git` directory is NOT accessible via browser:
  - Visit `https://yourdomain.com/.git/` — should return **403 Forbidden** or **404 Not Found**
  - Visit `https://yourdomain.com/.git/config` — should return **403 Forbidden** or **404 Not Found**
- [ ] HTTPS redirects HTTP traffic correctly (visit `http://yourdomain.com`)
- [ ] No sensitive files accessible via browser (`.env`, `config.yaml`, etc.)

### Performance Check

- [ ] Page loads within 3 seconds on a standard connection
- [ ] Images and fonts load correctly
- [ ] No mixed content warnings (HTTP resources on HTTPS page)

---

## Automatic Deployment Verification

### If Using GitHub Webhooks

- [ ] Webhook shows green ✅ in GitHub → repo → Settings → Webhooks → Recent Deliveries
- [ ] Test: make a small cosmetic change, push, verify it appears on the live site within 1 minute

### If Using Cron Job

- [ ] Cron job is listed in cPanel → Cron Jobs
- [ ] Deployment log exists and shows successful pulls: `cat ~/logs/deploy.log`
- [ ] Test: make a small change, push, wait for cron interval, verify it appears

---

## Rollback Procedure

If the deployment introduces a problem:

1. [ ] Identify the last known-good commit hash:
   ```bash
   cd /home/<username>/mcadv-repo && git log --oneline -10
   ```
2. [ ] Roll back:
   ```bash
   git reset --hard <commit-hash>
   ```
3. [ ] Verify the site is back to the correct state
4. [ ] Fix the issue in a new commit and redeploy

---

## Common Issues Quick Reference

| Symptom | First Check |
|---------|-------------|
| Site shows old content | Webhook/cron triggered? Check `~/logs/deploy.log` |
| 403 on all pages | File permissions: `chmod 644 website/*.html` |
| 404 on all pages | Document root points to correct `website/` path? |
| `.git` directory accessible | `.htaccess` present and correctly configured? |
| Webhook shows 500 error | `git status` on server — merge conflicts? |
| cPanel deploy fails | Authentication token expired? |

---

*See [docs/CPANEL_DEPLOYMENT.md](CPANEL_DEPLOYMENT.md) for the complete deployment guide.*
