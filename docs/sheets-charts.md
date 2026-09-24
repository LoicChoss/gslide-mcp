# Native Sheets charts on slides

Two servers, one flow. The **Sheets MCP** owns the data and builds the chart in a
spreadsheet; **gslide-mcp** embeds that chart on a slide, linked, and refreshes it.
The model orchestrates the two; the servers never talk to each other.

## Flow

1. **Spreadsheet.** Either the user's (an export, a reporting workbook: pass its URL)
   or a new one for the deck (Sheets MCP `create_spreadsheet`, named like the deck).
2. **Data.** Sheets MCP `write_values`: one block per chart (categories in the first
   column, one series per column, a header row), formulas welcome (`SUM`, N / N-1 - 1,
   ROAS = collecte / dépenses).
3. **Chart.** Sheets MCP `manage_chart add` with `chart_type`, `domain`, `series`,
   `title`, `legend`, `stacked`; it returns the chart id.
4. **Slide.** gslide-mcp `insert_sheets_chart(deck, slide, spreadsheet, chart_id, x, y, w, h)`
   (`linked=True` by default). Position it like a component: under the title, full
   content width.
5. **Adjust.** The chart is an ordinary element: `transform_element(deck, element_id, x_pt, y_pt, width_pt, height_pt)` moves and resizes it, `zorder`, `duplicate_element` and `delete_elements` apply; its id comes from `insert_sheets_chart`, `list_sheets_charts` or `inspect_slide` (type `chart`).
6. **Later.** Data changes in the spreadsheet → `refresh_sheets_charts(deck)`; the
   slide follows. `list_sheets_charts(deck)` says what is linked to what.

Tables are not linkable: Slides only links charts. Compute the table in Sheets
(totals, deltas, ROAS), read it with the Sheets MCP `read_range`, and write it with
the `table` component (`total_row`, `delta_cols`, `icons`).

## Which charts go native

| Drawn component (v1) | Sheets chart | Notes |
|---|---|---|
| `chart_bars` | `column` / `bar` | per-bar colours need the Sheets-side extension below |
| `chart_grouped` | `column` / `bar`, two series | N dark / N-1 light needs series colours |
| `chart_stacked` | `column` / `bar` + `stacked` / `percent` | |
| `chart_line` | `line` | dashed series need the extension |
| `chart_combo` | `COMBO` (bars + line on the right axis) | not exposed by the Sheets MCP yet |
| `donut`, `donut_row`, `pie` | `doughnut` / `pie` | slice colours follow the **spreadsheet theme** |
| `mini_charts` | several `column` charts | |
| `bubbles` | `BUBBLE` | not exposed yet |
| `gauge`, `target`, `compare_bars` | `SCORECARD` / `bar percent` | different look; keep drawn |
| everything else | — | stays drawn (`insert_component`) |

Rule: native and linked when the figures will move (recurring bilans, dashboards);
drawn when the slide is frozen or the chart has no Sheets equivalent.

## What the Sheets side must be able to set (charter)

The Sheets API supports all of this; the Sheets MCP `manage_chart` exposes only the
first block today. Needed for charter-faithful native charts:

- **Exposed today**: type (column, bar, line, area, stepped_area, scatter, pie, doughnut),
  stacked / percent, title, subtitle, axis title, legend position, size, anchor.
- **Series**: colour per series (`colorStyle`), colour per point, `targetAxis` (left /
  right), `type` per series (bars + line = `COMBO`), line dash and width, point shape,
  data labels on / off with their text format.
- **Pie / doughnut**: `pieHole` (0.5 for the charter donut), slice labels
  (`LABELED_LEGEND` or data labels); slice colours come from the spreadsheet's theme,
  so the **spreadsheet theme** must be settable: `spreadsheetTheme.themeColors`
  (ACCENT1…6 = acide, menthe, cyan, corail, magenta, violet; TEXT = navy; BACKGROUND =
  white) and `primaryFontFamily` = Barlow. One call per spreadsheet, then every chart
  is on-charter by default.
- **Text**: `fontName` (Barlow) and `titleTextFormat` / axis / legend text formats
  (size, bold, colour); `backgroundColorStyle` (white, or transparent on coloured slides).
- **Axes**: `viewWindow` min / max, number format, hidden axis; gridline colour is not
  settable (keep Google's light grey or hide the gridlines).
- **Chart types to add**: `COMBO`, `BUBBLE`, `SCORECARD`, `HISTOGRAM`, `WATERFALL`, `TREEMAP`.

Charter values to feed the theme: `#002B3C` navy, `#FFFFFF` white, `#EDEDED` gray,
`#E8FF00` acid, `#00F5B5` mint, `#45DBFF` cyan, `#FF9170` coral, `#FA00A6` magenta,
`#9E38FF` violet (the `periscope` theme of this server, `themes/periscope.json`).

## Verified live (2026-09-22)

A spreadsheet created with the charter as `spreadsheetTheme` (Barlow, navy text, the
six accents) and three charts built with the raw Sheets API (doughnut with `pieHole`
0.55, two-series `COLUMN` with `colorStyle` navy / grey and data labels, `COMBO` bars
+ line on `RIGHT_AXIS`) embedded linked on a slide, listed and refreshed: all good,
Barlow and colours honoured. Two findings:

- Pie / doughnut slices start at **ACCENT2** of the theme, not ACCENT1 (Google, the
  first slice, took ACCENT2). Order the theme accents with that in mind, or set the
  colours per series where the API allows it (basic charts).
- Slides keeps the chart's aspect ratio inside the box (a 600 × 371 px chart in a
  200 × 160 pt box renders 200 × 124, centred): size the box to the chart's ratio.

## Verified end to end with the two MCPs (2026-09-24)

Sheets MCP `create_spreadsheet` → `set_theme periscope` → `write_values` (formulas
included) → `manage_chart add` ×3 with `style: periscope` (`doughnut` + `pie_hole`,
`column` + `series_colors` + `data_labels`, `combo` + `series_types` + `series_axes`)
→ Slides MCP `insert_sheets_chart` ×3 → a cell changed in the sheet →
`refresh_sheets_charts` (the bar moved) → `transform_element` on the doughnut (moved
and resized, link kept). Barlow, charter colours and legends rendered as in Sheets.

Geometry: Google fits the chart in the requested box and **recentres it** at the
chart's aspect (a 430 × 160 pt box holds a 600 × 371 px chart as 258.8 × 160 centred,
so `list_sheets_charts` reports x 335.6, not 250). A linked chart's base size is tiny
(30 000 EMU) with a large scale: `transform_element` works on the displayed size, so
the scale values it reports look big; that is normal.

## Sizing on a 960 × 540 pt Periscope slide

Full-width chart under a title: `x_pt=40, y_pt=110, width_pt=880, height_pt=380`.
Two side by side: width 430 each, gap 20. A chart built 600 × 371 px in Sheets keeps its
aspect when scaled; give the box the same ratio (1.6) or set the Sheets chart size to
the box's ratio to avoid letter-boxing.
