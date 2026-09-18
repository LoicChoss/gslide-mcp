# gslide-mcp

A Python MCP server that exposes typed tools for building and editing Google Slides decks. It wraps the [gslides-api](https://pypi.org/project/gslides-api/) library and adds MCP tooling on top: markdown-aware text writing, slide screenshots, cross-deck copying, and a template-library workflow that lets you assemble new decks from slide fragments across any number of source decks.

## Why this exists

The Google Slides REST API and its Python client are expressive but verbose — a single formatted text update takes five nested request dicts. This server pre-composes the most common operations into typed MCP tools so a language model can build polished decks without reconstructing boilerplate every session. A small set of semantic shortcuts (`swap_client`, `fetch_logo_by_domain`, `assemble_from_template`) cover the tedious parts of agency-style deck work.

## Status

Early release. The API surface may shift between minor versions. Contributions welcome. Not affiliated with or endorsed by Google.

## Install

Requires Python 3.11 or newer.

```sh
git clone https://github.com/jemmanuele/gslide-mcp.git
cd gslide-mcp
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .
```

The entry point `gslides-mcp` is now on your PATH inside the venv.

## First-run setup (OAuth)

Full walkthrough: [docs/oauth-setup.md](docs/oauth-setup.md)

Three-step distillation:

1. In the [Google Cloud Console](https://console.cloud.google.com), create a **Desktop app** OAuth 2.0 Client ID with the Slides API and Drive API enabled.
2. Download the client-secret JSON, rename it `credentials.json`, and save it to `~/.gslides-mcp/creds/credentials.json`.
3. The first MCP tool call opens a browser tab for Google consent. After approval, `token.json` is written next to your credentials file (mode `0o600`) and reused from then on, with automatic refresh.

Required OAuth scopes:

```
https://www.googleapis.com/auth/presentations
https://www.googleapis.com/auth/drive
```

To store credentials somewhere other than `~/.gslides-mcp/creds/`, set `GSLIDES_MCP_CRED_DIR` to the desired directory before launching the server.

## Wiring it up to a client

Add the server to your Claude Desktop or Claude Code MCP config:

```json
{
  "mcpServers": {
    "gslides": {
      "command": "gslides-mcp"
    }
  }
}
```

If the entry point is not on your system PATH, use the full path to the venv binary, e.g. `"/path/to/venv/bin/gslides-mcp"`.

For debugging outside a client, run the server directly:

```sh
python -m gslides_mcp.server
```

### Claude Desktop one-click install (`.mcpb`)

A prebuilt bundle is attached to each [GitHub release](https://github.com/jemmanuele/gslide-mcp/releases). Download `gslide-mcp-<version>.mcpb`, double-click it (or drag it onto Claude Desktop → Settings → Extensions), and fill in the settings form:

- **Credentials directory** — where your `credentials.json` lives (defaults to `~/.gslides-mcp/creds`).
- **Apps Script web-app URL** / **logo.dev token** — optional, leave empty unless you set those up.
- **Theme** — default theme for components (`periscope`).
- **Assets folder (Drive)** — shared folder (id or URL) holding the PNG pictos, logos and screenshots that `card` icons and the `browser` / `laptop` mockups use; local files passed to those props are uploaded there.

The bundle uses the `uv` runtime: Claude Desktop provisions Python and the dependencies from `pyproject.toml` / `uv.lock` itself, so nothing needs to be installed beforehand. You still need to create `credentials.json` once (see [First-run setup](#first-run-setup-oauth)).

To build the bundle locally (requires Node.js):

```sh
npx @anthropic-ai/mcpb validate manifest.json
npx @anthropic-ai/mcpb pack . dist/gslide-mcp-0.2.0.mcpb
```

`.mcpbignore` keeps docs, examples, virtualenvs and any local `credentials.json` / `token.json` out of the archive.

## Tool overview

| Group | Tool | What it does |
|-------|------|--------------|
| **Deck** | `create_presentation` | Create a new blank deck; returns `{presentation_id, url}` |
| | `clone_deck` | Copy an existing deck via Drive |
| | `list_slides` | List slides with index, object ID, and summary |
| | `inspect_slide` | Inspect all elements on a slide (optionally recursive) |
| | `find_elements` | Search elements by type, alt-title, or text content |
| | `get_presentation` | Raw `presentations.get` passthrough with an optional `fields` mask (auto-trimmed to 200 kB) |
| | `get_page` | One page — slide, layout, master or notes — raw, or `compact=True` for one line per element |
| | `export_pres` | Export to local `.pptx` or `.pdf` |
| | `batch_apply` | Raw `batchUpdate` escape hatch for unsupported operations |
| | `raw_request` | GET/POST any Slides API path under the presentation (Drive refused) |
| **Layout** | `list_layouts` | Masters and layouts with placeholders and per-slide usage counts |
| | `screenshot_layout` | Render one layout page inline; `annotate=True` renders the placeholder-key map |
| | `screenshot_layouts` | Vertical strip of every layout (or a chosen list), captioned by name |
| | `create_slide_from_layout` | New slide on a layout with placeholders filled from markdown — one atomic batch |
| | `build_from_outline` | A run of slides from `[{layout, fills}, …]` — all names resolved first, one atomic batch |
| | `relayout_slide` | Rebuild a slide on another layout and delete the original (destructive) |
| **Slide** | `create_slide` | Insert a new blank slide at a given position |
| | `duplicate_slide` | Duplicate a slide within the same deck |
| | `move_slide` | Reorder a slide |
| | `delete_slides` | Delete one or more slides |
| | `set_slide_hidden` | Hide slides from presentation mode ("Skip slide") or show them again; `list_slides` flags them `hidden` |
| | `set_background` | Set the slide background color (solid hex) |
| | `get_speaker_notes` | Read a slide's speaker notes |
| | `set_speaker_notes` | Replace (or clear) a slide's speaker notes |
| **Shape** | `create_shape` | Insert a shape |
| | `insert_image` | Insert an image by URL or Drive file ID |
| | `insert_image_local` | Insert a local PNG/JPEG/GIF (temporary Drive upload, cleaned up) |
| | `set_fill` | Set the fill color of a shape |
| | `set_outline` | Set the outline of a shape |
| **Table** | `create_table` | Create a table (≤ 20×20), optionally pre-filled, in one batch |
| | `edit_table` | Insert/delete rows and columns |
| | `set_table_cell` | Write markdown into one cell |
| **Content** | `write_text_markdown` | Write bold/italic/bullets in one call via gslides-api's markdown writer |
| | `batch_write_markdown` | Batch version of `write_text_markdown` (~N× faster for multi-element updates) |
| | `set_text` | Set plain text on a shape |
| | `style_text` | Apply text styles (font, size, color) to a range |
| | `replace_text` | Find-and-replace text across a slide or deck |
| **Element** | `transform_element` | Move an element (absolute or relative pt) |
| | `zorder` | Change element stacking order |
| | `duplicate_element` | Duplicate an element within a slide |
| | `delete_elements` | Delete one or more elements |
| **QA** | `screenshot` | Capture a slide as an inline image |
| | `screenshot_range` | Capture a range of slides |
| | `overlap_check` | Detect overlapping elements on a slide |
| **Components** | `list_components` | Catalogue of 50 themed components (KPI, cards, callouts, badges, pills, numbered lists, agenda, big numbers, phase cards, compare / before-after panels, quote, table, heatmap, bar / line / stacked / combo charts, pie, donut, gauge, target, funnel, timeline, process, hub & spoke, tree, flowchart, stack, matrices, team and logo grids, Google-result / browser / laptop / phone mockups) plus themes and the assets folder |
| | `insert_component` | Render a component at a position — one atomic batch, grouped as one element |
| | `draw` | Primitive ops (box, text runs with `==highlight==`, arrowed lines, polyline, arc, ring, table, image from URL or assets folder) in one batch |
| | `save_component` | Freeze a JSON recipe as a reusable component |
| | `delete_component` | Remove a saved recipe |
| **Comments** | `manage_comments` | List, read, create (unanchored), reply to/resolve, delete Drive comments |
| **Cross-deck** | `copy_slide_cross_deck` | Copy a slide from one deck to another (requires Apps Script — see below) |
| | `cross_deck_ping` | Health-check the Apps Script web app |
| **Semantic** | `swap_client` | Clone a deck and rebrand it (logo swap, name replacement) in one call |
| **Assets** | `list_assets` | Names available in the Drive assets folder (pictos, logos, photos, screenshots) |
| | `fetch_logo_by_domain` | Resolve a public logo URL for a brand by domain |
| **Library** | `summarize_deck` | Build a structured slide index for a single deck |
| | `build_template_library` | Summarize multiple decks into a reusable JSON registry |
| | `assemble_from_template` | Assemble a new deck from cherry-picked slides across decks |

Every tool carries MCP annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`) so clients can tell reads from writes and flag the destructive ones (`delete_*`, `relayout_slide`, `edit_table`, `manage_comments`, `batch_apply`, `raw_request`).

## Components and themes

Slides has no design system, so this server carries one: a **theme** (palette, roles, font, named text styles — `periscope` and `default` ship, add yours in `~/.gslides-mcp/themes/`) and **components** that only speak in roles and style names, rendered as native shapes in one `batchUpdate`. Charts included — bars, lines and donuts are drawn with shapes, no images and no linked Sheets. Pictos, logos and screenshots (card icons, browser and laptop mockups) come from one shared Drive folder — `GSLIDES_MCP_ASSETS_FOLDER` — where a local file is uploaded once and tinted variants are generated per theme. When no component fits, `draw` gives the primitives, and `save_component` turns a sketch into a reusable JSON recipe. Guide: [docs/components.md](docs/components.md).

## Claude Code skill: `gslides-prez`

[.claude/skills/gslides-prez/SKILL.md](.claude/skills/gslides-prez/SKILL.md) is a gated workflow for building a client deck from a template deck with this server: framing (which layout for title slides, which for content slides), numbered plan, copy, build on an emptied clone, visual check, then a "what to improve in the skill" wrap-up. `periscope.md` next to it holds reusable agency material. It loads automatically in this repo; to use it from any project, link it into your personal skills:

```powershell
New-Item -ItemType Junction -Path "$HOME\.claude\skills\gslides-prez" -Target "<repo>\.claude\skills\gslides-prez"
```

## Working with layouts

The theme of a deck lives in its masters and layouts. `list_layouts` shows them with their placeholders, `screenshot_layouts` renders them, and `build_from_outline` turns an ordered outline of `{layout, fills}` into slides in one atomic batch. Full guide with a worked example: [docs/layouts.md](docs/layouts.md).

Three things the Slides API does not allow, and this server does not work around:

1. **Creating a layout** — there is no `createLayout` request. Layouts come from the theme (or from a template deck you `clone_deck`).
2. **Changing the layout of an existing slide** — `slideProperties.layoutObjectId` is read-only. `relayout_slide` rebuilds the slide on another layout and deletes the original; it is a rebuild, not a switch.
3. **Importing a theme from another deck** — masters and layouts cannot be copied between presentations. Start from a copy of the deck whose theme you want.

## Optional: cross-deck copy via Apps Script

`copy_slide_cross_deck` and `assemble_from_template` route through a small Google Apps Script web app because the Slides REST API has no cross-presentation copy endpoint.

Setup guide: [docs/appscript-setup.md](docs/appscript-setup.md)

Once deployed, save the web-app URL to `~/.gslides-mcp/appscript_url` (one line, no quotes) or set `GSLIDES_MCP_APPSCRIPT_URL` in your environment. Without this configured, those two tools raise a descriptive error with setup instructions.

## Optional: logo.dev for `fetch_logo_by_domain`

`fetch_logo_by_domain` tries Wikipedia Commons, then Brandfetch CDN, then a Google favicon fallback by default. To enable the [logo.dev](https://logo.dev) source as an additional candidate:

```sh
export GSLIDES_MCP_LOGODEV_TOKEN=your_token_here
```

Without this variable set, logo.dev is skipped entirely and the fallback chain still produces a usable URL.

## The template-library workflow

See [docs/template-library.md](docs/template-library.md) for the full walkthrough and [examples/template_library_workflow.md](examples/template_library_workflow.md) for a concrete worked example.

In brief: `build_template_library` ingests a list of deck IDs into a JSON registry, you review and annotate it, then `assemble_from_template` pulls the slides you want into a new deck in the order you specify.

## Project layout

```
gslide-mcp/
├── README.md
├── LICENSE                         MIT license
├── pyproject.toml
├── appscript/
│   └── cross_deck_copy.gs          Apps Script web app for cross-deck copy
├── manifest.json                   Claude Desktop .mcpb bundle manifest
├── CHANGELOG.md
├── docs/
│   ├── oauth-setup.md              Google OAuth setup walkthrough
│   ├── appscript-setup.md          Apps Script deployment guide
│   ├── layouts.md                  Building slides on the theme's layouts
│   ├── components.md               Components, themes, draw ops, recipes
│   └── template-library.md         Template library workflow
├── examples/
│   └── template_library_workflow.md  Worked example
├── tests/                          pytest suite (mocked API) + opt-in live test
└── src/gslides_mcp/
    ├── server.py                   MCP entry point
    ├── auth.py                     OAuth + service client
    ├── app.py                      MCP application instance + annotation presets
    ├── util.py                     Shared helpers (ids, geometry, layout lookup, markdown)
    ├── draw.py                     Primitive ops → Slides requests (the canvas)
    ├── themes/                     Theme engine + periscope.json / default.json
    ├── components/                 Registry, built-in components, JSON recipes
    └── tools/
        ├── deck.py                 create / list / inspect / find / export / batch_apply
        ├── layout.py               element layout + slide layouts (list, screenshot, build, relayout)
        ├── slides.py
        ├── notes.py                speaker notes
        ├── shapes.py
        ├── images.py               insert_image_local
        ├── tables.py
        ├── content.py
        ├── qa.py
        ├── comments.py             Drive comments on the deck
        ├── components.py           list/insert components, draw, save/delete recipes
        ├── raw.py                  raw_request escape hatch
        ├── cross_deck.py
        ├── semantic.py
        ├── assets.py
        └── library.py
```

## Running the tests

```sh
uv run --with pytest pytest tests
```

The suite runs against an in-memory fake of the Slides/Drive API (`tests/conftest.py`, fixtures in `tests/fixtures/`). One live round-trip is opt-in — point it at a deck the OAuth account can edit:

```sh
GSLIDES_MCP_INTEGRATION_DECK=<presentation id> uv run --with pytest pytest tests/test_integration.py
```

## Contributing

Bug reports and pull requests are welcome at https://github.com/jemmanuele/gslide-mcp/issues.

## License

MIT. See [LICENSE](LICENSE).
