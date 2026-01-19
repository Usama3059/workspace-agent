# Google AI & Workspace Setup Guide

This guide explains how to configure Google AI (Gemini) and Google Workspace (OAuth) for the Agent.

## 1) Google AI Setup (Gemini)

To use Gemini models, you need an API key.

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Click on **"Get API key"**.
3. Create a new API key or use an existing one.
4. Add the key to your `.env` file:
   ```env
   GEMINI_API_KEY="your_api_key_here"
   ```

## 2) Google Workspace Setup (OAuth)

To allow the agent to access your Gmail, Drive, Calendar, etc., you need OAuth credentials.

### A) Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a **New Project**.

### B) Enable Required APIs

Search for and enable the following APIs in the Library:

- **Gmail API**
- **Google Drive API**
- **Google Calendar API**
- **Google Docs API**
- **Google Sheets API**
- **Google Slides API**

### C) Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**.
2. Select **User Type: External** (or Internal for Workspace domains).
3. Fill in the required App Information.
4. **Crucial:** Add your email as a **Test User** in the "Test users" section.

### D) Create Client ID & Secret

1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > OAuth client ID**.
3. Select **Web application** (or Desktop app depending on your usage).
4. Add Authorized Redirect URIs:
   - `http://localhost`
   - `http://localhost:8080/`
5. Save and copy the **Client ID** and **Client Secret**.
6. Add them to your `.env` file:
   ```env
   GOOGLE_OAUTH_CLIENT_ID="your_client_id"
   GOOGLE_OAUTH_CLIENT_SECRET="your_client_secret"
   USER_GOOGLE_EMAIL="your_email@gmail.com"
   ```

## 3) Alternative: Configuration via Streamlit UI

Instead of manually editing the `.env` file, you can use the Streamlit interface:

1. Run the app (`streamlit run app.py` or via Docker).
2. Open the sidebar.
3. Use the **"Google AI"** and **"Google OAuth"** sections to paste your keys and Client IDs.
4. Click **"Save Settings"** to persist them.

## 4) First-time Authorization

When you run the agent for the first time, it will prompt you with a link to authorize access. Follow the browser instructions to grant the requested permissions.

---

**Note:** Keep your `.env` file private and never commit it to version control.
