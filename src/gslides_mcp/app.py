"""Single shared FastMCP instance and the tool annotation presets.

Tool modules import `mcp` from here and register handlers with
``@mcp.tool(annotations=...)``. Keeping it in its own module avoids circular
imports.

Annotations are MCP hints (``mcp.types.ToolAnnotations``). Note the protocol
defaults: ``destructiveHint`` is *true* unless stated, so additive writers say
``destructiveHint=False`` explicitly.
"""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("gslides-mcp")

# Reads nothing but the deck (or the web); changes nothing.
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False)

# Creates or moves things; never deletes or overwrites existing content.
ADDITIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=False)

# Overwrites a value; calling twice with the same input leaves the same state.
IDEMPOTENT = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)

# Can delete or irreversibly alter content (or, for escape hatches, anything).
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True)
