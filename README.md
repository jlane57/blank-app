# Harrison Cross Country

Streamlit site for Harrison Cross Country team records, athlete results, and
meet data. The records, athlete, season, and meet pages use the shared boys'
and girls' team spreadsheet.

The **Data Interactive** page provides filtered comparisons across athletes,
meets, seasons, and recorded team performance. It includes charts, detailed
result tables, 5K-only filtering, and CSV downloads for comparison results.

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

Durable app-owned writes also require `GOOGLE_SERVICE_ACCOUNT_JSON`. The app
checks Streamlit secrets first and then the process environment, so a GitHub
preview can use GitHub-provided secrets when Streamlit secrets are unavailable.
For a Codespaces preview, add these secrets under the repository's **Codespaces
secrets** using the exact names below; Codespaces exposes them as environment
variables:

```text
SPREADSHEET_ID
ADMIN_PASSWORD
GOOGLE_SERVICE_ACCOUNT_JSON
GOOGLE_DRIVE_FOLDER_ID       # only when photo uploads are enabled
```

For a GitHub Actions preview, repository secrets are not automatically
environment variables. Map them explicitly on the preview step, for example:

```yaml
env:
  SPREADSHEET_ID: ${{ secrets.SPREADSHEET_ID }}
  ADMIN_PASSWORD: ${{ secrets.ADMIN_PASSWORD }}
  GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
  GOOGLE_DRIVE_FOLDER_ID: ${{ secrets.GOOGLE_DRIVE_FOLDER_ID }}
```

Share only this workbook with the service-account email, and never commit the
JSON key.

For the complete Google Cloud project, service-account, Sheet, Drive folder,
least-privilege sharing, and verification checklist, see
[`GOOGLE_SETUP.md`](./GOOGLE_SETUP.md). The app authenticates directly from the
server with the service account; it does not expose a Google credential or
write endpoint to visitors.

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

The Admin page's Website Availability controls are stored in the workbook's
`Site Settings` tab. Turning the website off stays off until an administrator
turns it back on; it does not automatically re-enable itself. The site-wide
banner follows the same rule. Existing `site_status.json` settings are imported
when the tab is first created.

### News

The public **News** page displays team updates. Administrators can publish and
delete entries from the Admin Portal; each entry has a headline, body, and
publication date. News is stored in the workbook's `News` tab. Existing
[`news.json`](./news.json) entries are imported when the tab is first created.

### Photos

Administrators can upload images to Google Drive from the Admin Portal. Add
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

Runtime Python dependencies are pinned in
[`requirements.txt`](./requirements.txt) and
[`pyproject.toml`](./pyproject.toml), with the legacy page-local list in
[`Pages/requirements.txt`](./Pages/requirements.txt) kept aligned. Resolved hashes and
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
over HTTPS to the private `Bug Reports` tab in the workbook configured by
`SPREADSHEET_ID`. Reports include their submission time and text only; do not
ask users to include personal or sensitive information. The report tab has no
public read path.

The server writes to the workbook with a restricted Google service account.
Configure `GOOGLE_SERVICE_ACCOUNT_JSON` in Streamlit Community Cloud secrets or
as a GitHub Codespaces secret for local preview. Share only the target workbook
with that service-account email, and grant no broader Drive access unless photo
uploads are enabled. The older Apps Script receiver in
[`bug_report_receiver.gs`](./bug_report_receiver.gs) is retained as a reference
for existing deployments but is not used by the current app.

### Durable app-owned storage

The workbook is the durable source of truth for app-owned data. The app creates
these tabs when needed:

- `Bug Reports` — private, append-only anonymous reports.
- `News` — published announcements.
- `Site Settings` — website availability and banner settings.
- `Photo Gallery` — metadata for images stored in the configured Google Drive
  folder.

Storage writes are conservative by default: reports and new news entries are
appended, settings update only their known keys, and generic row replacement
requires an explicit destructive permission. Admin deletion controls are
separate from ordinary save actions, and meet-result overwrites remain behind
the existing explicit overwrite option. The app does not clear unrelated
workbook tabs or rows as part of normal reads or writes.

Existing local `news.json` and `site_status.json` data is imported the first
time the corresponding workbook tab is empty. Future app data should use a
new, explicitly named tab and a versioned header rather than deployment-local
files. Google storage is more durable than deployment files, but it still
requires normal backups and credential/usage monitoring; no external service
can guarantee zero outages or zero maintenance.

### Workbook structure

The records page reads manually maintained individual, team, and
amphitheater record tabs. Boys' and girls' data may be kept in separate tabs
named `Boys Individual Records`, `Girls Individual Records`,
`Boys Team Records`, `Girls Team Records`, `Boys Amp Records`, and
`Girls Amp Records`. The older combined `Athlete Records`, `Team Records`, and
`Amp Records` layout remains supported, with boys' data in the left block and
girls' data in the right block.

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
