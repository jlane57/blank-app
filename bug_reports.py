import requests


def submit_bug_report(message, web_app_url, secret):
    report_text = message.strip()
    if not report_text:
        raise ValueError("Enter a description before submitting.")
    if len(report_text) > 5000:
        raise ValueError("The description must be 5,000 characters or fewer.")
    if not web_app_url.strip() or not secret.strip():
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
