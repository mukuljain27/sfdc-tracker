# SFDC Jira Daily Tracker

Team dashboard showing module-wise open SFDC issue counts for the BIRDEYE project.
Auto-updates at **9:00 AM** and **6:30 PM IST** (weekdays) via GitHub Actions.

## Setup (one-time, ~5 minutes)

### 1. Create the GitHub repo
1. Go to https://github.com/new
2. Name it `sfdc-tracker` (or any name)
3. Set visibility to **Private** (recommended) or Public
4. Click **Create repository**
5. Upload all files from this folder into the repo

### 2. Enable GitHub Pages
1. Go to repo → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `(root)`
4. Click **Save**
5. Your URL will be: `https://<org>.github.io/sfdc-tracker/`

### 3. Add Jira API credentials as Secrets
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token** → give it a name → copy the token
3. In GitHub repo → **Settings → Secrets and variables → Actions → New secret**
   - Name: `JIRA_EMAIL`  Value: your Atlassian email (e.g. mukul.jain@birdeye.com)
   - Name: `JIRA_TOKEN`  Value: the API token you just created
4. That's it — the token is never exposed in the HTML

### 4. Test it
1. Go to repo → **Actions → Update SFDC Tracker → Run workflow**
2. Watch it fetch data and commit updated `index.html`
3. Open your GitHub Pages URL — you should see live data

## How it works
- GitHub Action runs at 9 AM IST → fetches Jira, saves as **morning count**
- GitHub Action runs at 6:30 PM IST → fetches Jira, saves as **evening count**
- The dashboard shows morning vs evening per module + resolved today delta
- History tab tracks last 7 days
- The Jira API token is stored only in GitHub Secrets — never in the HTML

## Manual update
Go to **Actions → Update SFDC Tracker → Run workflow** any time to refresh.
