function doPost(e) {
  const properties = PropertiesService.getScriptProperties();
  const expectedSecret = properties.getProperty("BUG_REPORT_SECRET");
  const sheetId = properties.getProperty("BUG_REPORT_SHEET_ID");
  const payload = JSON.parse(e.postData.contents);

  if (!expectedSecret || payload.secret !== expectedSecret) {
    return jsonResponse({ ok: false });
  }

  if (
    typeof payload.message !== "string" ||
    payload.message.trim().length === 0 ||
    payload.message.length > 5000
  ) {
    return jsonResponse({ ok: false });
  }

  if (!sheetId) {
    throw new Error("BUG_REPORT_SHEET_ID is not configured.");
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const spreadsheet = SpreadsheetApp.openById(sheetId);
    const sheet =
      spreadsheet.getSheetByName("Bug Reports") ||
      spreadsheet.insertSheet("Bug Reports");
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(["Submitted at (UTC)", "Report"]);
    }
    sheet.appendRow([new Date(), payload.message.trim()]);
  } finally {
    lock.releaseLock();
  }

  return jsonResponse({ ok: true });
}

function jsonResponse(payload) {
  return ContentService.createTextOutput(JSON.stringify(payload)).setMimeType(
    ContentService.MimeType.JSON
  );
}
