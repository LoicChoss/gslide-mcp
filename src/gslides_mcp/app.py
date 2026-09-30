"""Single shared FastMCP instance and the tool annotation presets.

Tool modules import `mcp` from here and register handlers with
``@mcp.tool(annotations=...)``. Keeping it in its own module avoids circular
imports.

Annotations are MCP hints (``mcp.types.ToolAnnotations``). Note the protocol
defaults: ``destructiveHint`` is *true* unless stated, so additive writers say
``destructiveHint=False`` explicitly.
"""

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

# Sent to the client with the tool list. Without it, Claude picked this server as
# soon as someone asked for a PowerPoint ("build it in Slides, export to .pptx").
INSTRUCTIONS = """\
Google Slides only: these tools build and edit Google Slides decks in the user's Drive.
When the user asks for a PowerPoint (PowerPoint, PPT, .pptx) or a Keynote, do not use this
server: make the file with the usual PowerPoint tooling. Use it for such a request only when
the user explicitly wants the result in Google Slides. export_pres downloads a Google Slides
deck that already exists, when the user asks for that download; it is not a way to make a
PowerPoint."""

mcp = FastMCP("gslides-mcp", instructions=INSTRUCTIONS)

# Reads nothing but the deck (or the web); changes nothing.
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False)

# Creates or moves things; never deletes or overwrites existing content.
ADDITIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=False)

# Overwrites a value; calling twice with the same input leaves the same state.
IDEMPOTENT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)

# Can delete or irreversibly alter content (or, for escape hatches, anything).
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True)
