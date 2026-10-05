"""The template a new deck starts from, and the folder it lands in, when the user names none.

Set once in the Desktop bundle: ``GSLIDES_MCP_DEFAULT_TEMPLATE`` (*Template par
défaut*) and ``GSLIDES_MCP_DEFAULT_FOLDER`` (*Dossier de rangement par défaut*),
each an id or a URL. Local server only: the hosted connector takes nothing but
its URL in Claude, so there is no per-person setting there.
"""

from __future__ import annotations

import os

from .util import parse_drive_id

ENV_TEMPLATE = "GSLIDES_MCP_DEFAULT_TEMPLATE"
ENV_FOLDER = "GSLIDES_MCP_DEFAULT_FOLDER"


def _read(name: str) -> str | None:
    raw = os.environ.get(name, "").strip()
    # an optional field left empty may reach us as its literal placeholder
    if not raw or raw.startswith("${"):
        return None
    return parse_drive_id(raw)


def template_id() -> str | None:
    return _read(ENV_TEMPLATE)


def folder_id() -> str | None:
    return _read(ENV_FOLDER)
