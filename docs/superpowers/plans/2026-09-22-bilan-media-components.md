# Bilan média components Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the MCP the components a média bilan needs (grouped bars, régie colours, KPI notes, ad scoreboard, media plan, arrow timeline…) and align every chart on the pptx reference style (thin lines, light grid, legend on top).

**Architecture:** Components stay pure functions `render(props, theme, w, h) -> (ops, height)` over the `draw` ops canvas; new shared chart furniture (grid/axis/legend/label thinning/panel) lives in `components/axes.py`; new components go in two new modules (`charts3.py`, `reporting.py`) registered from `components/__init__.py`. Theme gains régie tokens/roles and two colour helpers.

**Tech Stack:** Python 3.11, pytest (`uv run --no-sync pytest`), Google Slides API via `draw.ops_to_requests`.

Spec: `docs/superpowers/specs/2026-09-22-bilan-media-components-design.md`.

---

### Task 1: Theme régie roles, `tint`, `is_dark`
- Modify: `src/gslides_mcp/themes/periscope.json`, `default.json`, `themes/__init__.py`
- Test: `tests/test_themes.py` — `regie_*` roles resolve in both themes; `tint("meta", 0.5)` returns a lighter hex; `is_dark("navy")` True, `is_dark("mint")` False.
- Commit: `feat(theme): régie colour roles, tint and is_dark helpers`

### Task 2: draw ops — dashed box outline, per-row table heights
- Modify: `src/gslides_mcp/draw.py` (`box`: `line.dash` → `outline.dashStyle`; `table`: `row_heights`)
- Test: `tests/test_draw.py` — dash appears in `updateShapeProperties`; table with `row_heights=[20, 60, 20]` creates one `updateTableRowProperties` per distinct height and the frame height is 100.
- Commit: `feat(draw): dashed outlines and per-row table heights`

### Task 3: shared chart style in `axes.py`
- Modify: `src/gslides_mcp/components/axes.py` — `GRID_W=0.5`, `LINE_W=1.5`, `MARKER=4`, `y_axis_ops` uses `chart_grid`; `baseline_op(px, y, pw)` (`chart_axis`, 1 pt); `thin_labels(labels, slot, size) -> list[str|None]`; `legend_ops(entries, x, y, w, pos)` (entries `{name, color, kind: box|line}`, centred when `pos == "top"`); `panelize(ops, height, w, title, panel)`.
- Test: `tests/test_components6.py::test_axes_helpers` — thinning keeps first/last, legend centred, panel adds a surface box and shifts ops.
- Commit: `feat(charts): shared grid, baseline, legend, label thinning and panel helpers`

### Task 4: restyle existing charts
- Modify: `builtin.py` (`chart_bars` colors/title/panel + style; `chart_line` 1.5 pt, markers 4, grid), `axes.py` (`chart_combo`: legend_pos top, markers auto, show_values auto, thin labels), `charts2.py` (`chart_stacked` baseline/grid/legend_pos), `donut` labels/legend_pos/title/panel.
- Test: update `tests/test_components5.py` expectations (legend on top, markers auto), add assertions in `test_components6.py` (chart_bars `colors`, donut `labels`).
- Commit: `refactor(charts): align chart_bars, chart_line, chart_combo, chart_stacked and donut on the pptx style`

### Task 5: `chart_grouped`, `donut_row`, `mini_charts` (`components/charts3.py`)
- Test: grouped bars per category with tints, horizontal variant values, donut_row repeats donut with titles, mini_charts shares categories and colours.
- Commit: `feat(components): chart_grouped, donut_row, mini_charts`

### Task 6: `kpi` note, `kpi_grid` rows, `table` icons / delta_cols / row_heights
- Modify: `builtin.py`
- Test: note run is muted and smaller; rows add a label column; icons add a 26 pt column with image ops; delta_cols colours cells by sign.
- Commit: `feat(components): kpi note, kpi_grid rows, table icons and delta columns`

### Task 7: reporting blocks (`components/reporting.py`): `analysis_block`, `source_note`, `stat_box`, `takeaways`, `placeholder`
- Test: chevrons reused, box outline optional; source note italic caption right-aligned with platform line; stat boxes with operator; placeholder dashed.
- Commit: `feat(components): analysis_block, source_note, stat_box, takeaways, placeholder`

### Task 8: `ad_scoreboard`, `gallery`
- Test: table transposed with header names, image row height, images placed over cells, dashed placeholders when no image, top_note; gallery ratio and placeholders.
- Commit: `feat(components): ad_scoreboard and gallery`

### Task 9: `media_plan`, `timeline_arrow`
- Test: levers with logos and budget/dates lines, objective panel width = split; arrow line with end_arrow, boxes alternate above/below, dashed style.
- Commit: `feat(components): media_plan and timeline_arrow`

### Task 10: catalogue text, docs, changelog
- Modify: `components/uses.py` (one `use` per new component), `docs/components.md`, `README.md`, `CHANGELOG.md`.
- Test: `test_components6.py::test_every_component_has_use_and_example_renders` (both themes).
- Commit: `docs: bilan média components`

### Task 11: visual check on a test deck
- Script in scratchpad using repo code + `.env.local` creds: create deck « gslides-mcp · test composants · 2026-09 », one slide per component (pptx-like data), then `screenshot_range`; fix rendering issues; re-run.
