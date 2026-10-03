# Corpus Metadata Studio — GitHub + Streamlit setup

This app follows the 12 fields in Dr. Sara Khan's supplied metadata workbook. Each signed-in user can create private corpora, add/edit/delete metadata records, import a workbook, and download a formatted Excel file with a Field Guide sheet.

## What you need

1. GitHub, for storing the app code.
2. Streamlit Community Cloud, for hosting the app.
3. Supabase, for Google authentication and persistent metadata storage.
4. Google Cloud, for a Google OAuth web client.

Google sign-in is handled by Google Identity Services, then the identity token is exchanged with Supabase Auth. Supabase still owns the user accounts and database. The app uses the Supabase user session for database access, and row-level security keeps each user's data separate. The project administrator retains database administrator access.

## Step 1 — Create the Supabase project and tables

1. Create a project at [supabase.com](https://supabase.com). Keep its database password private.
2. Open **SQL Editor**, choose a new query, paste all of `setup.sql`, and click **Run** once. It creates the tables and privacy policies. It is intended for a new project; do not run it repeatedly.
3. Open **Project Settings → API** (or **API Keys**) and copy the project URL and the **publishable key**. A legacy **anon** key also works. Never put a `secret` or `service_role` key in this app.

## Step 2 — Create Google sign-in credentials

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. Configure the OAuth consent screen. Add an app name, support email, and contact email. If the app is in **Testing** mode, add the Google accounts that will test it as test users. To let people outside the test list sign in, configure and publish the consent screen as appropriate for your account and Google verification requirements.
3. Create an OAuth client ID with application type **Web application**.
4. In **Authorized JavaScript origins**, add the exact origin of the deployed Streamlit app (for example, `https://your-app-name.streamlit.app`). Do not include a path or trailing slash. If you also test locally, add `http://localhost:8501`.
5. In Supabase, open **Authentication → Sign In / Providers → Google**. Enable Google, then copy the Google **Client ID** and **Client Secret** into the matching fields. Save the provider settings. If Supabase displays a callback URL for Google, add that URL to Google's **Authorized redirect URIs** as well.

Google and Supabase screens can change over time, but the key values are the Web application Client ID and Client Secret in Supabase, and the matching Client ID plus allowed app origin in Streamlit/Google.

## Step 3 — Upload the app files to GitHub

1. Download and extract the ZIP.
2. Create a GitHub repository, for example `corpus-metadata-studio`.
3. Upload the contents of the `metadata_app` folder to the repository root. Include `app.py`, `metadata.py`, `requirements.txt`, `setup.sql`, `README.md`, `secrets.example.toml`, `.gitignore`, and the complete `google_login` folder containing `index.html`.
4. Do not upload a real `secrets.toml`, student workbooks, passwords, tokens, or database administrator keys.

## Step 4 — Deploy on Streamlit

1. Open [Streamlit Community Cloud](https://share.streamlit.io), connect GitHub, and select **Create app**.
2. Choose your repository and branch, and set **Main file path** to `app.py`.
3. Under **Advanced settings → Secrets**, add the following, replacing the placeholders with your actual values:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "YOUR-PUBLISHABLE-OR-LEGACY-ANON-KEY"
GOOGLE_CLIENT_ID = "YOUR-WEB-APPLICATION-CLIENT-ID.apps.googleusercontent.com"
```

4. Deploy. Confirm that the deployed app's exact HTTPS origin is listed under Google's **Authorized JavaScript origins**. Add your users as Google test users if the consent screen is still in Testing mode.
5. Click **Continue with Google**. First-time Google sign-in creates the Supabase Auth account automatically; users do not need to wait for a Supabase confirmation email. Existing email/password accounts can still use the email login expander.

Secrets belong in Streamlit's **Settings → Secrets**, not in `app.py` or GitHub. The app only needs the Google Client ID; keep the Google Client Secret in Supabase and never in Streamlit or GitHub.

## How to use it

1. Sign in with Google. Use the sidebar to create a corpus, such as `PAWAC — Fall 2026`.
2. Select **New record**. Enter the exact corpus filename under File ID and fill the other fields. Click **Save record**.
3. To edit, select a saved File ID, change its fields, and save. Deletion requires the confirmation checkbox.
4. To import a workbook, upload it and click **Import new records**. The app reads the `Student Metadata` sheet, or the first sheet if that sheet is absent. All 12 columns are required. Existing File IDs in that corpus are skipped; duplicates within the uploaded file are rejected. Each import accepts at most 2,000 rows and 5 MB. Format identifiers such as roll numbers as text in Excel to preserve leading zeros.
5. Review the preview and click **Download my metadata (.xlsx)**. Names and roll numbers are omitted by default; uncheck the option to include them. Other fields, including Notes, may still identify a person and should be reviewed before sharing.
6. Each user's records are separate. Two users may use the same corpus name and File IDs. A filename must be unique within one corpus.

The signed-in session is retained for the active Streamlit session. Closing/reloading the browser or an expired session may require signing in again. Saved records remain in Supabase. Logout clears the session's client and widgets. Editing the same record in two browser tabs uses the last successful save; avoid simultaneous edits to that record.

## Optional local run (VS Code terminal)

Use Python 3.12. Open the `metadata_app` folder in VS Code. In **Terminal → New Terminal**, run:

```bash
python -m venv .venv
```

On Windows, activate it:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS/Linux, activate it:

```bash
source .venv/bin/activate
```

Then install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` from `secrets.example.toml`, fill in the Supabase values and Google Client ID, and allow `http://localhost:8501` in Google Cloud's authorized JavaScript origins. Then start Streamlit:

```bash
python -m streamlit run app.py
```

## Verification before sharing

The code's syntax, metadata validation, and Excel export can be checked offline. Live Google/Supabase authentication, database policies, and browser operation require your configured projects.

1. Sign in as test user A, create a corpus and a record.
2. Sign in as test user B in a private/incognito window. A's corpus and record must not appear.
3. Create the same corpus name and File ID as B. Download as each account and check that each file contains that account's own records.
4. Close/reopen the app, sign in again, and confirm records persist.
5. Import a small workbook, edit a record, delete it, and check the Excel output.

## Troubleshooting

- **Google button is missing:** confirm the `google_login/index.html` file and folder were uploaded to GitHub, and `GOOGLE_CLIENT_ID` is present in Streamlit Secrets. Restart/reboot the app after changing secrets.
- **Google says app not authorized:** confirm the deployed Streamlit origin exactly matches an Authorized JavaScript origin in Google Cloud. If the consent screen is in Testing mode, add the account as a test user.
- **Google login fails at Supabase:** confirm the Google provider is enabled in Supabase and the Client ID and Client Secret match the Google Web application credentials.
- **Setup incomplete:** set `SUPABASE_URL`, `SUPABASE_KEY`, and `GOOGLE_CLIENT_ID` in Streamlit Secrets. Use only the publishable/anon key in the app.
- **Cannot load or create records:** run `setup.sql` once, check that the Supabase project is active, and confirm you used its publishable/anon key.
- **Cannot save:** check that File ID is unique in the selected corpus.
- **Import fails:** use `.xlsx`, keep the exact column headers, and remove duplicate File IDs.
- **An old version is still deployed:** confirm the repository contains the latest files and allow Streamlit to redeploy.

## Official references

- [Google sign-in with Supabase](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Supabase JavaScript sign-in with ID token](https://supabase.com/docs/reference/javascript/auth-signinwithidtoken)
- [Supabase row-level security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Streamlit Community Cloud deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app)
- [Streamlit secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
