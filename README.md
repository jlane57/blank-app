# Harrison Cross Country

Streamlit site for Harrison Cross Country team records, athlete results, and
meet data. The records, athlete, season, and meet pages use the shared boys'
and girls' team spreadsheet.

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

### Guarded meet-result imports

The Admin page includes a guarded **Import Meet Results** workflow. It accepts
CSV/TSV, XLSX, UTF-8 text, text-based PDF, and PNG/JPEG uploads when the
deployment has its OCR engine configured. Uploads are limited to 10 MB and 500
result rows. Names are matched against the selected roster and race times are
validated using the same rules as the public pages.

The import is intentionally review-first and has separate Boys and Girls tabs.
The `Team` column (`B` or `G`) is used to prevent cross-team matches. The admin
can select an existing meet or create one; new meets are inserted in date order.
For a new meet, the admin enters its name, race type, location, date, notes, and
the selected team's place. Imported times are strings in `MM:SS[.DDD]` format,
with trailing fractional zeroes omitted. Every value written by the importer is
italicized. The admin can edit suggested athlete names and times in the colored
confidence preview and review table, must correct invalid or unmatched rows, and
must confirm every row. Existing results are protected from overwrite unless
the admin explicitly enables the overwrite option. The approved result is a
downloadable XLSX copy; the live Google Sheet is never modified automatically.
This avoids accidental publication and does not require an AI API or a Google
write credential. PDF/image OCR failures are shown as errors and never produce
a success-shaped export.

The deployment installs the Tesseract system package from
[`packages.txt`](./packages.txt) for PNG/JPEG OCR. PDF extraction handles
text-based PDFs through `pypdf`; image-only/scanned PDFs require a deployment
with a PDF rendering/OCR pipeline and are rejected clearly when that is not
available.

### Persistent site controls

The Admin page's Website Availability controls are stored in
[`site_status.json`](./site_status.json) using an atomic file replacement.
Turning the website off stays off until an administrator turns it back on; it
does not automatically re-enable itself. The site-wide banner follows the same
rule: its enabled state and message remain unchanged until an administrator
saves new settings. Legacy status files migrate safely with the banner disabled.

### News

The public **News** page displays team updates. Administrators can publish and
delete entries from the Admin Center; each entry has a headline, body, and
publication date. News is stored in the deployment's ignored
[`news.json`](./news.json) file using atomic replacement, so publishing does
not modify the spreadsheet.

### Photos

Administrators can upload images to Google Drive from the Admin Center. Add
these secrets to enable uploads:

```toml
GOOGLE_SERVICE_ACCOUNT_JSON = "{...}"
GOOGLE_DRIVE_FOLDER_ID = "your-drive-folder-id"
```

Share the Drive folder with the service-account email as an Editor. The
service account must also have edit access to the spreadsheet. The app creates
or updates the `Photo Gallery` tab with these columns:
`file_id`, `display_url`, `thumbnail_url`, `caption`, `date_uploaded`,
`category`, `related_key`, `photographer`, `alt_text`, `approved`, and
`featured`.

Approved public images remain in Drive; the spreadsheet stores metadata and
links only. The app limits uploads to 10 MB and displays no more than six
featured Home images or ten Meet images at a time.

### Dependency and deployment policy

Runtime Python dependencies are pinned in both
[`pyproject.toml`](./pyproject.toml) and
[`Pages/requirements.txt`](./Pages/requirements.txt), with resolved hashes and
transitive versions recorded in [`uv.lock`](./uv.lock). Deployments use
`uv sync --locked` so an unattended dependency upgrade cannot change behavior.
The dev container installs only the explicitly listed Tesseract package; it
does not run a broad operating-system upgrade.

The project uses established, documented libraries: Streamlit for the UI,
Pandas/openpyxl for workbook data, Plotly for charts, pypdf for text-based PDF
extraction, Requests for HTTPS, and pytesseract as the Python wrapper for the
Tesseract OCR executable. External services and OCR can still fail, so the app
surfaces errors and refuses to generate an approved import when extraction is
uncertain. No software can be guaranteed never to break; pinned dependencies,
tests, and explicit failure paths reduce that risk.

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

### Workbook structure

The records page reads the `Athlete Records`, `Team Records`, and `Amp Records`
tabs. Each record tab contains boys' data in the left block and girls' data in
the right block.

### Year-tab structure

All four-digit year tabs use the current shared-team layout:

- Rows above the athlete header contain race type, location, date, notes, boys'
  place, and girls' place. Additional title or coaches rows may appear before
  this metadata. The header row has `Name`, `Grade`, and `Team` in columns
  A:C, with meet names beginning in column D. Athlete rows start immediately
  below the header.
- `Team` is `B` for boys or `G` for girls. This shared roster powers the Boys
  Varsity, Boys JV, Girls Varsity, and Girls JV views without separate tabs.
- Each meet's results are in its corresponding meet column.
- Bold an athlete's name in column A to include them in the season's postseason
  roster.

Keep race times as strings in `MM:SS[.DDD]` (for example, `16:25` or
`16:25.347`). Trailing fractional zeroes are omitted. Unformatted numeric
values are not guessed as times. Blank or unparseable results are omitted from
athlete result views. An athlete's progression chart includes timed results only
when that meet's race type contains `5k` (case-insensitive).
