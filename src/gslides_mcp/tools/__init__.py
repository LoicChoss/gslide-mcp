"""Tool modules. Each module registers its tools with the shared FastMCP server.

Importing this package imports all submodules, which is when @mcp.tool() decorators
fire and register tool handlers.
"""

from . import (  # noqa: F401
    assets, comments, components, content, cross_deck, deck, images, layout, library, notes, qa, raw,
    semantic, shapes, slides, tables,
)
