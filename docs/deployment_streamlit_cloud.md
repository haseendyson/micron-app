# MicrON Deployment Guide - Streamlit Cloud

## Prerequisites Checklist

- [ ] GitHub account (free)
- [ ] Streamlit Cloud account (free tier available)
- [ ] OpenAI API Key (for the LLM)
- [ ] Your code pushed to GitHub

---

## Step 1: Prepare Your Repository

### 1.1 Create/Update `.streamlit/secrets.toml`

This file stores sensitive API keys. **Do NOT commit this to GitHub.**

```toml
OPENAI_API_KEY = "sk-xxxxxxxxxxxxx"
CONFIG_FILE = "configs/micron_healthcare_futures.toml"
```

### 1.2 Ensure `.gitignore` Excludes Secrets

Check that `.streamlit/secrets.toml` is in your `.gitignore`:

```
.streamlit/secrets.toml
.venv/
__pycache__/
```

### 1.3 Verify `requirements.txt` (Alternative to Pipfile)

Streamlit Cloud works best with `requirements.txt`. Create one from your Pipfile:

```bash
pipenv requirements > requirements.txt
```

Or you can use the existing `Pipfile` and Streamlit will handle it, but `requirements.txt` is more reliable.

---

## Step 2: Push to GitHub

```bash
# From your workspace
cd /workspaces/micro-narratives-app-main

# Initialize git if not already done
git init

# Add your remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/micro-narratives-app.git

# Commit and push
git add .
git commit -m "Add MicrON healthcare futures configuration"
git push -u origin main
```

---

## Step 3: Deploy on Streamlit Cloud

### 3.1 Sign Up for Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "Sign Up" → Choose "Sign up with GitHub"
3. Authorize Streamlit to access your GitHub repos

### 3.2 Create New App

1. Click **"New App"** button
2. Select:
   - **GitHub repo:** `micro-narratives-app` (or your repo name)
   - **Branch:** `main`
   - **File path:** `app.py`

### 3.3 Add Secrets on Streamlit Cloud

1. Click the **⋮ (three dots)** → **Settings** on your deployed app
2. Go to **Secrets** tab
3. Paste your secrets:

```toml
OPENAI_API_KEY = "sk-xxxxxxxxxxxxx"
CONFIG_FILE = "configs/micron_healthcare_futures.toml"
```

4. **Save** and your app will auto-restart with the secrets

---

## Step 4: Configure for Prolific Integration (Optional)

If you want to integrate Prolific for participant recruitment:

1. Add Prolific study link to app with URL parameters
2. Capture `participant_id` from URL:

```
https://your-app.streamlit.app?participant_id=PROLIFIC_PID
```

Your app already supports this! The code handles URL parameters:
```python
url_participant_id = st.query_params.get("pid") or st.query_params.get("participant_id")
```

---

## Step 5: Test Your Deployment

Your app will be live at:
```
https://micron.streamlit.app
```
(or whatever name you chose)

**Test checklist:**
- ✓ Consent page displays correctly
- ✓ Demographic questions work
- ✓ AI conversation flows properly
- ✓ Scenario generation works
- ✓ No API key errors in logs

---

## Troubleshooting

### App won't load?
- Check **Logs** (⋮ → Logs)
- Verify OPENAI_API_KEY is set correctly in Secrets
- Check Pipfile/requirements.txt includes all dependencies

### API Key error?
```
streamlit.errors.StreamlitAPIException: No OpenAI API Key found
```
→ Make sure `OPENAI_API_KEY` is in Secrets, not just local `.streamlit/secrets.toml`

### Dependencies missing?
- Run: `pip freeze > requirements.txt`
- Commit and push to GitHub
- Streamlit will auto-reinstall

### App times out?
- Increase timeout in Streamlit settings if needed
- Cloud runs have 2GB RAM limit (usually fine)

---

## Optional: Custom Domain

To use your own domain (e.g., `micron.yourorg.com`):

1. Go to app Settings → Custom domains
2. Add your domain and follow DNS instructions
3. Update Prolific study link to your custom domain

---

## Next Steps

1. **Push to GitHub** with the MicrON config
2. **Deploy on Streamlit Cloud** (5 minutes)
3. **Add OPENAI_API_KEY** to Secrets
4. **Test the app** - share link with participants
5. **Monitor** via Logs tab if issues arise

---

## Data & Analytics

- Streamlit Cloud logs all activity
- Data flows to DynamoDB (if configured with AWS credentials)
- Responses stored anonymously per your privacy policy

---

**Need help with any step? Let me know!** 🚀
