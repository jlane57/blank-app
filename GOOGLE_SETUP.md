# Google service-account setup

This is the deployment checklist for the app's Google Sheets and Drive
storage. It uses server-side service-account authentication; do not use an
Apps Script web app or put a service-account key in the repository.

## 1. Create the Google Cloud project

1. Create a dedicated Google Cloud project for this site.
2. Enable **Google Sheets API** and **Google Drive API**.
3. Create a service account with no project-level roles. The app uses access
   granted directly on the specific spreadsheet and image folder.
4. Create a JSON key once, download it securely, and keep it in a password
   manager or deployment secret store. Do not email it, paste it into an
   issue, or commit it.

The service account needs only access to the resources below. Do not grant
`Owner`, `Editor` at the project level, or broad Shared Drive access.

## 2. Create and share the storage resources

1. Create the production Google Sheet.
2. Copy only its document ID from the URL:
   `https://docs.google.com/spreadsheets/d/<DOCUMENT_ID>/edit`
3. Create a dedicated Google Drive folder for site images.
4. Share the Sheet with the service-account `client_email` as **Editor**.
5. Share the image folder with that same email as **Editor**.
6. Do not share the spreadsheet or folder with the service-account email's
   parent organization unless that is intentionally required.

The app creates the `Bug Reports`, `News`, `Site Settings`, and `Photo Gallery`
tabs as needed. The existing year and record tabs remain manually maintained.
The app stores image metadata in `Photo Gallery` and image files in the
dedicated Drive folder.

## 3. Configure the deployment

Set these values in the deployment's secret manager:

```text
SPREADSHEET_ID=<document ID only>
ADMIN_PASSWORD=<long unique password>
GOOGLE_SERVICE_ACCOUNT_JSON=<complete JSON key contents>
GOOGLE_DRIVE_FOLDER_ID=<folder ID only>
```

`GOOGLE_DRIVE_FOLDER_ID` is required for photo uploads. The other three values
are required for the app's persistent storage and administrator controls.
Never put these values in committed files.

For Streamlit Community Cloud, add them under the app's **Settings > Secrets**.
For Codespaces, add them as repository or user secrets so they become
environment variables. For GitHub Actions, map repository secrets explicitly
to the deployment step; repository secrets are not automatically exported.

## 4. Verify before going live

Use a staging Sheet and staging folder first. Confirm all of the following:

- Public pages can read the existing year tabs.
- The Admin page can sign in and save Site Settings.
- Publishing and deleting a test News item works.
- A test photo uploads to the intended folder and appears on the public page.
- An anonymous bug report creates a row in `Bug Reports`.
- The service-account email cannot access any unrelated test Sheet or folder.
- No key, secret, or full credential JSON appears in logs or source control.

After verification, remove staging test rows and keep a documented backup of
the production Sheet. Rotate the service-account key if it was ever exposed.

## Operational limits

This setup avoids the additional endpoint and shared-secret risks of Apps
Script, but it cannot guarantee zero outages, quota exhaustion, bad source
data, or credential compromise. Keep regular Sheet backups, monitor deployment
errors, and rotate credentials according to the organization's policy.
