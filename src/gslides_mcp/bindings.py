"""The « Liaisons » tab of a bilan spreadsheet: which deck element follows which range.

Format (``docs/bilan-sync.md``): a header row ``type | élément | source |
options`` in any order, then one binding per row. ``parse_bindings`` checks
every row and returns the good ones and, separately, the errors with their row
number in the tab, so ``sync_deck`` can report them all before writing.
"""

from __future__ import annotations

from googleapiclient.errors import HttpError

from .sheets_source import read_values
from .util import fold_text

TAB = "Liaisons"
_TYPES = {"texte": "texte", "text": "texte", "tableau": "tableau", "table": "tableau", "image": "image"}
_COLUMNS = {"type": "type", "element": "element", "source": "source", "options": "options"}
_CHOICES = {
    "texte": {"delta": ("auto", "true", "false", "inverse")},
    "tableau": {"style": ("slides", "sheets", "charter"), "rows": ("keep", "fit"), "columns": ("keep", "fit")},
    "image": {"fit": ("inside", "crop")},
}
_NUMBERS = {"tableau": ("row_height",)}


def _options(kind: str, raw: str) -> dict:
    out: dict = {}
    for part in (p.strip() for p in raw.split(";")):
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"option {part!r} is not key=value")
        key, value = (x.strip() for x in part.split("=", 1))
        key, low = key.lower(), value.lower()
        if key in _CHOICES[kind]:
            if low not in _CHOICES[kind][key]:
                raise ValueError(f"{key}={value!r}: expected one of {', '.join(_CHOICES[kind][key])}")
            out[key] = {"true": True, "false": False}.get(low, low) if key == "delta" else low
        elif key in _NUMBERS.get(kind, ()):
            try:
                out[key] = float(value.replace(",", "."))
            except ValueError:
                raise ValueError(f"{key}={value!r} is not a number") from None
            if out[key] <= 0:
                raise ValueError(f"{key} must be positive")
        else:
            known = sorted(set(_CHOICES[kind]) | set(_NUMBERS.get(kind, ())))
            raise ValueError(f"unknown option {key!r} for {kind} (known: {', '.join(known)})")
    return out


def parse_bindings(rows: list[list[str]]) -> tuple[list[dict], list[dict]]:
    """``([{row, type, element, source, options}], [{row, error}])`` from the tab's values; row numbers are the tab's."""
    if not rows:
        raise ValueError(f"the « {TAB} » tab is empty: see docs/bilan-sync.md for its format")
    index = {}
    for j, name in enumerate(rows[0]):
        key = _COLUMNS.get(fold_text(str(name)).strip().lower())
        if key:
            index[key] = j
    missing = [c for c in ("type", "element", "source") if c not in index]
    if missing:
        raise ValueError(f"the « {TAB} » tab needs the columns type, élément, source (options optional); missing: "
                         f"{', '.join(missing)}")
    bindings, errors, seen = [], [], {}
    for n, row in enumerate(rows[1:], start=2):
        def col(key: str) -> str:
            j = index.get(key)
            return str(row[j]).strip() if j is not None and j < len(row) else ""

        kind_raw, element, source = col("type"), col("element"), col("source")
        if not (kind_raw or element or source) or kind_raw.startswith("#"):
            continue
        kind = _TYPES.get(fold_text(kind_raw).lower())
        try:
            if kind is None:
                raise ValueError(f"type {kind_raw!r}: expected texte, tableau or image")
            if not element:
                raise ValueError("élément is empty")
            if not source:
                raise ValueError("source is empty")
            if element in seen:
                raise ValueError(f"{element!r} is already bound on row {seen[element]}")
            options = _options(kind, col("options"))
        except ValueError as exc:
            errors.append({"row": n, "error": str(exc)})
            continue
        seen[element] = n
        bindings.append({"row": n, "type": kind, "element": element, "source": source, "options": options})
    return bindings, errors


def read_bindings(spreadsheet: str) -> tuple[list[dict], list[dict]]:
    """The spreadsheet's « Liaisons » tab, parsed."""
    try:
        (rows,) = read_values(spreadsheet, [f"'{TAB}'!A1:E500"])
    except HttpError as exc:
        raise ValueError(f"no « {TAB} » tab in this spreadsheet ({exc.resp.status}): create it with the Sheets MCP, "
                         "see docs/bilan-sync.md") from None
    return parse_bindings(rows)
