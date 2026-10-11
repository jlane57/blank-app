# Harrison Boys' Cross Country

Streamlit site for Harrison Boys' Cross Country team records, athlete results,
and meet data.

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
SPREADSHEET_ID = "***REMOVED***"
ADMIN_PASSWORD = "choose-a-strong-password"
```

The local secrets file is ignored by Git. Update either value here for local testing. For Streamlit Community Cloud, add or update both keys under the app's **Settings > Secrets**. Use a strong admin password; changing it in the secrets settings takes effect on the next app run. All team pages are public to anyone with the site link; only the Admin page requires `ADMIN_PASSWORD`.

### Anonymous bug reports

The **Report a Bug** sidebar page is public, does not ask for an identity, and sends reports
over HTTPS to a private Google Sheet using the Apps Script receiver in
[`bug_report_receiver.gs`](./bug_report_receiver.gs). Reports include their
submission time and text only; do not ask users to include personal or sensitive
information. Google may process technical request metadata as part of operating
the service.

To enable submissions:

1. Create a Google Sheet for private report storage.
2. Open **Extensions > Apps Script** from the Sheet and copy the contents of
   `bug_report_receiver.gs` into the script editor.
3. In Apps Script **Project Settings > Script Properties**, add:
   - `BUG_REPORT_SHEET_ID`: the ID from the Google Sheet URL.
   - `BUG_REPORT_SECRET`: a long, randomly generated secret.
4. Deploy the script as a **Web app**, executing as yourself and accessible to
   **Anyone**. The shared secret in the POST body protects the write operation;
   the Sheet itself should remain private.
5. Add the deployed `/exec` URL and the same secret to Streamlit secrets:

   ```toml
   BUG_REPORT_WEB_APP_URL = "https://script.google.com/macros/s/DEPLOYMENT_ID/exec"
   BUG_REPORT_SECRET = "use-the-same-long-random-secret"
   ```

Submissions are sent by the Streamlit server, not directly by the visitor's
browser. They are protected in transit by HTTPS and stored in the private Sheet;
this is not end-to-end encryption.

### Year-tab structure

All four-digit year tabs are read using either supported worksheet layout:

- In the current layout, rows above the athlete header contain meet type,
  location, date, notes, and team place. The header row has `Name`, `Grade`,
  and `Best` in columns A:C, with meet names beginning in column D. Athlete
  rows start immediately below the header.
- The previous layout has `Name` and `Grade` in columns A:B, meet names in
  column D onward, metadata rows immediately below the header, and athlete rows
  below the metadata.
- In either layout, each meet's results are in its corresponding meet column.
- Bold an athlete's name in column A to include them in the season's postseason
  roster.

Keep race times as `MM:SS` (for example, `16:25`) or `HH:MM:SS` (for example,
`0:16:25`). Values are interpreted as elapsed time and displayed consistently as
`MM:SS` or `MM:SS` with a fractional part only when significant (for example,
`16:25.12`, not `16:25.120`). Formatted Excel time/duration cells are read as
typed durations. Improvement deltas use `-` for faster and `+` for slower, keep
the zero-padded minute field (for example, `-00:15`), and omit insignificant
fractional zeros. Unformatted numeric values are not guessed as times, to avoid
silently introducing inaccurate results. Blank or unparseable results are
omitted from athlete result views. An athlete's progression chart includes timed
results only when that meet's `Meet Type` contains `5k` (case-insensitive).
