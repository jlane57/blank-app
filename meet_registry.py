import json
import uuid
from pathlib import Path

from spreadsheet_storage import read_rows, replace_rows, storage_configured

REGISTRY_SHEET = "Meet Registry"
REGISTRY_FILE = Path(__file__).with_name("meet_registry.json")
REGISTRY_COLUMNS = ["meet_id", "source_key", "year", "name", "date", "location", "type"]


def _text(value):
    return str(value or "").strip()


def _fingerprint(meet):
    return (
        _text(meet.get("year")),
        _text(meet.get("date")).casefold(),
        _text(meet.get("location")).casefold(),
        _text(meet.get("type")).casefold(),
    )


def _new_id():
    return f"meet_{uuid.uuid4().hex}"


def _read_registry():
    if storage_configured():
        rows = read_rows(REGISTRY_SHEET)
        if not rows:
            return []
        indexes = {str(value).strip(): index for index, value in enumerate(rows[0])}
        return [
            {
                column: _text(row[indexes[column]])
                if indexes.get(column) is not None and indexes[column] < len(row)
                else ""
                for column in REGISTRY_COLUMNS
            }
            for row in rows[1:]
            if row and indexes.get("meet_id") is not None
            and indexes["meet_id"] < len(row) and _text(row[indexes["meet_id"]])
        ]
    try:
        values = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    return values if isinstance(values, list) else []


def assign_meet_ids(meets):
    """Attach persistent IDs to workbook meets and synchronize the registry sheet."""
    registry = _read_registry()
    by_source = {entry["source_key"]: entry for entry in registry if entry["source_key"]}
    by_fingerprint = {_fingerprint(entry): entry for entry in registry}
    changed = False

    for meet in meets:
        source_key = f"{meet['year']}:{meet['column']}"
        entry = by_source.get(source_key) or by_fingerprint.get(_fingerprint(meet))
        if entry is None:
            entry = {"meet_id": _new_id()}
            registry.append(entry)
            changed = True
        values = {
            "meet_id": entry["meet_id"],
            "source_key": source_key,
            "year": _text(meet.get("year")),
            "name": _text(meet.get("name")),
            "date": _text(meet.get("date")),
            "location": _text(meet.get("location")),
            "type": _text(meet.get("type")),
        }
        if values != entry:
            entry.update(values)
            changed = True
        meet["meet_id"] = entry["meet_id"]
        by_source[source_key] = entry
        by_fingerprint[_fingerprint(meet)] = entry

    if changed and storage_configured():
        replace_rows(
            REGISTRY_SHEET,
            REGISTRY_COLUMNS,
            [[entry[column] for column in REGISTRY_COLUMNS] for entry in registry],
            allow_destructive=True,
        )
    elif changed:
        REGISTRY_FILE.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return meets


def meet_options(meets):
    return [
        (
            f"{meet['name']} ({meet['year']})",
            meet["meet_id"],
        )
        for meet in sorted(
            meets,
            key=lambda item: (str(item.get("year", "")), str(item.get("name", "")).casefold()),
            reverse=True,
        )
        if meet.get("meet_id")
    ]
