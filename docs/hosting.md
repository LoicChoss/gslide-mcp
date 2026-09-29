# Hosting gslides-mcp for a team

One server, one URL. Each person adds the URL as a connector in Claude and
signs in with their own Google account; nobody handles an OAuth client, a
`credentials.json` or a token. Every call runs with the rights of the person
who made it.

## Google Cloud (once)

In a project that belongs to the Workspace organisation:

1. Enable the Google Slides, Google Drive and Apps Script APIs.
2. OAuth consent screen: audience **Internal** (only accounts of the domain
   can sign in, no Google verification needed). Scopes: `openid`,
   `userinfo.email`, `presentations`, `drive`.
3. OAuth client of type **Web application**, redirect URI
   `https://<host>/auth/callback` (plus `http://localhost:8000/auth/callback`
   to test locally).

## Server

The image (`Dockerfile`) serves streamable HTTP on port 8000 at `/mcp`, with
`/health` for the health check. Environment:

| Variable | |
|---|---|
| `GSLIDES_MCP_BASE_URL` | public URL, e.g. `https://slides.example.com` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | the Web application client |
| `GSLIDES_MCP_GOOGLE_DOMAIN` | optional: preselects accounts of the domain |
| `GSLIDES_MCP_APPSCRIPT_ID` | Script ID of the cross-deck copy script (below) |
| `GSLIDES_MCP_ASSETS_FOLDER` | Drive folder of named assets (default: the team folder); share it with the domain |
| `GSLIDES_MCP_THEME` | default theme (`periscope` when unset) |

Mount a volume on `/data`: it keeps sign-in sessions (encrypted with a key
derived from the client secret) and the shared themes and components. Without
it, everyone signs in again after each redeploy.

In Claude: Settings → Connectors → Add custom connector → `https://<host>/mcp`.

## Cross-deck copy

The web-app deployment runs as whoever deployed it, so the hosted server
refuses it. Create a **separate** Apps Script project with
`appscript/cross_deck_copy.gs`, its manifest limited to the `presentations`
and `drive` scopes, and deploy it as an **API executable** (steps at the top
of the file): its Cloud project must be the one holding the OAuth client, and
`GSLIDES_MCP_APPSCRIPT_ID` is its Script ID. Each copy then runs as the
signed-in user. Keep the existing web-app project as it is: local servers
(this one and google-sheets-mcp) still use it.

## What changes for tools

- `export_pres` returns a Google download `url` instead of a file path.
- `insert_image_local` takes `image_base64`; a `path` would name a file on the
  server and is refused.
- Themes and components saved with `save_component` are shared by the team.
