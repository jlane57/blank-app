# 🎈 Blank app template

A simple Streamlit app template for you to modify!

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://blank-app-template.streamlit.app/)

### How to run it on your own machine

Prerequisite: install `uv` if you don't already have it.

```
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

1. Sync the dependencies

   ```
   $ uv sync
   ```

2. Run the app

   ```
   $ uv run streamlit run streamlit_app.py
   ```

### Configure the spreadsheet

The app reads its spreadsheet ID and admin password from Streamlit secrets. For local testing, create `.streamlit/secrets.toml` with:

```toml
SPREADSHEET_ID = "your-spreadsheet-id"
ADMIN_PASSWORD = "choose-a-strong-password"
```

The local secrets file is ignored by Git. Update either value here for local testing. For Streamlit Community Cloud, add or update both keys under the app's **Settings > Secrets**. Use a strong admin password; changing it in the secrets settings takes effect on the next app run.
