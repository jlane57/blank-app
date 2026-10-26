import requests

from spreadsheet_storage import append_row, utc_timestamp

BUG_REPORT_SHEET = "Bug Reports"
BUG_REPORT_HEADERS = ("Submitted at (UTC)", "Report")


def submit_bug_report(message, web_app_url=None, secret=None):
    report_text = message.strip()
    if not report_text:
        raise ValueError("Enter a description before submitting.")
    if len(report_text) > 5000:
        raise ValueError("The description must be 5,000 characters or fewer.")
    if not web_app_url and not secret:
        append_row(BUG_REPORT_SHEET, BUG_REPORT_HEADERS, [utc_timestamp(), report_text])
        return
    if not web_app_url or not secret:
        raise ValueError("Bug report submission is not configured.")

    response = requests.post(
        web_app_url.strip(),
        json={"secret": secret.strip(), "message": report_text},
        timeout=15,
    )
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("The report service returned an invalid response.") from error

    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise RuntimeError("The report service could not accept this report.")
