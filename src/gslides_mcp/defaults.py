"""The template a new deck starts from, and the folder it lands in, when the user names none.

``GSLIDES_MCP_DEFAULT_TEMPLATE`` (*Template par défaut*) and
``GSLIDES_MCP_DEFAULT_FOLDER`` (*Dossier de rangement par défaut*), each an id or a
URL. Locally, the two fields of the Desktop bundle: one person's own. Hosted, the
server's environment: one template and one folder for the whole team, since the
connector takes nothing but its URL in Claude.
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
