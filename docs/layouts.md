# Building slides on the theme's layouts

A Google Slides deck carries its design in **masters** and **layouts**. A
layout is a page with placeholders (title, body, subtitle, picture…) that a
slide inherits — position, fonts, colors, bullets — so a slide built on the
right layout looks like the template without any styling calls.

This guide covers the `Layout` tool group: `list_layouts`,
`screenshot_layout` / `screenshot_layouts`, `create_slide_from_layout`,
`build_from_outline`, `relayout_slide`, plus the raw readers `get_page` and
`get_presentation`.

## What Google does not allow

Three limits of the Slides API, stated up front because the tools respect
them rather than paper over them:

| You might want to… | Reality | What to do instead |
|---|---|---|
| **Create a new layout** | There is no `createLayout` request. | Design layouts in the Slides editor (or in a template deck), then `clone_deck` it. You *can* edit an existing layout's own elements — element requests accept a layout as `pageObjectId` — but not add a layout. |
| **Change the layout of an existing slide** | `slideProperties.layoutObjectId` is read-only. | `relayout_slide` builds a new slide on the target layout, moves the content, deletes the original. It is a rebuild with known losses (see below), not a switch. |
| **Import a theme from another deck** | Masters/layouts cannot be copied between presentations. | Start from a copy of the deck whose theme you want (`clone_deck`), or copy whole slides across decks with `copy_slide_cross_deck` (Apps Script). |

## 1. See what the deck offers

```
list_layouts(presentation="1AbC…")
```

```json
{
  "masters": [
    {"master_id": "simple-light-2", "display_name": "Simple Light", "used_by_slides": 14}
  ],
  "layouts": [
    {"layout_id": "p2", "display_name": "Diapositive de titre", "name": "TITLE",
     "master_id": "simple-light-2", "used_by_slides": 1,
     "placeholders": [{"type": "CENTERED_TITLE", "index": 0, "object_id": "p2_i0"},
                      {"type": "SUBTITLE", "index": 0, "object_id": "p2_i1"}]},
    {"layout_id": "p4", "display_name": "Titre et corps", "name": "TITLE_AND_BODY",
     "master_id": "simple-light-2", "used_by_slides": 9,
     "placeholders": [{"type": "TITLE", "index": 0, "object_id": "p4_i0"},
                      {"type": "BODY", "index": 1, "object_id": "p4_i1"}]},
    {"layout_id": "p5", "display_name": "Titre et texte sur deux colonnes",
     "name": "TITLE_AND_TWO_COLUMNS", "master_id": "simple-light-2", "used_by_slides": 0,
     "placeholders": [{"type": "TITLE", "index": 0, "object_id": "p5_i0"},
                      {"type": "BODY", "index": 1, "object_id": "p5_i1"},
                      {"type": "BODY", "index": 2, "object_id": "p5_i2"}]}
  ]
}
```

- `used_by_slides` is computed from `slides[].slideProperties.layoutObjectId`.
- By default only layouts of masters that at least one slide uses are
  listed (`only_used_master=True`). Decks assembled from several sources
  accumulate orphan masters; pass `only_used_master=False` to see them.
- `index` is Google's placeholder index; it omits `0`, the tool fills it in.

To look at them: `screenshot_layouts(presentation)` returns one vertical
strip with every layout captioned by display name; `screenshot_layout(presentation, "Titre et corps")`
renders a single one. Both call `pages.getThumbnail` on the layout page
directly — nothing is written to the deck.

**Which key goes where?** Placeholder keys follow the layout's element
order, which is often *not* the visual order (a tree layout may have
`SUBTITLE[7]` as its top-left title and `SUBTITLE[0]` as the root box).
`screenshot_layout(presentation, "Arborescence02", annotate=True)` renders
the map: a temporary slide is created on the layout with each text
placeholder filled with its own key, captured, and deleted again. Read the
picture, then write your `fills`.

## 2. Address a layout by name

Every layout argument accepts a `layout_id` **or** a display name. Matching
order: exact id → exact display name → display name ignoring case and
accents (`"resume"` finds `"Résumé"`) → the API `name` (`TITLE_AND_BODY`).

If several layouts share a display name (typical after merging decks), the
call fails and lists each candidate with its id and master:

```
layout ref 'Arborescence' is ambiguous — 2 layouts match:
'Arborescence' (layout_id=p12, master=simple-light-2);
'Arborescence' (layout_id=g3a1, master=g3a1-master). Pass the layout_id instead.
```

Nothing is ever picked silently.

## 3. Fill placeholders

`fills` maps placeholder keys to markdown (same writer as
`write_text_markdown`: `**bold**`, `*italic*`, `- bullets`):

- a type present once on the layout is addressed by its name: `"TITLE"`,
  `"BODY"`, `"SUBTITLE"`, `"CENTERED_TITLE"`;
- a type present several times is addressed by position in page order:
  `"BODY[0]"`, `"BODY[1]"` (the order `list_layouts` shows). Using bare
  `"BODY"` on such a layout is an error that names the options;
- keys are case-insensitive; empty strings leave the placeholder untouched;
- unknown keys fail before anything is written, listing what the layout has;
- the order behind `BODY[0]`, `BODY[1]`… is the layout's element order, not
  the visual one — use `screenshot_layout(..., annotate=True)` to see it.

Under the hood the `createSlide` request pins the placeholders' object ids
via `placeholderIdMappings`, and the text requests target those ids in the
**same** `batchUpdate`. Inherited placeholders are born empty, so only
`insertText`-family requests are emitted — never `deleteText`, which would
make Google reject the whole batch.

## 4. Build a run of slides

```
build_from_outline(
  presentation="1AbC…",
  outline=[
    {"layout": "Diapositive de titre",
     "fills": {"CENTERED_TITLE": "Audit SEO — Q3", "SUBTITLE": "Periscope · septembre 2026"}},
    {"layout": "Titre et corps",
     "fills": {"TITLE": "Ce qu'il faut retenir",
               "BODY": "- **Trafic organique** : +18 % vs T2\n- 3 pages à corriger avant lancement\n- Budget netlinking à arbitrer"}},
    {"layout": "Titre et texte sur deux colonnes",
     "fills": {"TITLE": "Forces / faiblesses",
               "BODY[0]": "- Autorité de domaine\n- Contenu evergreen",
               "BODY[1]": "- Core Web Vitals mobiles\n- Maillage interne"}}
  ]
)
```

```json
[
  {"index": 15, "slide_id": "sl_1f2e3d4c5b", "layout_name": "Diapositive de titre"},
  {"index": 16, "slide_id": "sl_6a7b8c9d0e", "layout_name": "Titre et corps"},
  {"index": 17, "slide_id": "sl_a1b2c3d4e5", "layout_name": "Titre et texte sur deux colonnes"}
]
```

`index` is **1-based** — the same number `list_slides` shows and
`screenshot`, `screenshot_range`, `delete_slides` accept
(`screenshot_range(deck, ["15", "16", "17"])` renders exactly these three).
The `insertion_index` *argument*, on the other hand, is 0-based, like
`create_slide` and `move_slide` and the underlying API.

Guarantees:

- every layout name and every fill key is resolved **before** any write; if
  anything is wrong the error lists all problems (`outline[2]: no placeholder 'FOOTER' …`) and the deck is untouched;
- all slides go in **one** `batchUpdate`. If Google rejects it, nothing is
  created — there is no half-built run to clean up;
- `insertion_index` (0-based) positions the first slide; the others follow.
  Default appends at the end.

For a single slide, `create_slide_from_layout` takes the same `fills` and
additionally returns `placeholders_filled` / `placeholders_left_empty`, so
you can see at a glance that a `SLIDE_NUMBER` or `PICTURE` placeholder was
left alone. Follow up with `screenshot(presentation, slide_id)` to check the
result.

## 5. Move a slide to another layout (`relayout_slide`)

Because the layout of a slide can't be changed, `relayout_slide` does the
next best thing, in two batches:

1. create a new slide on the target layout right after the original, copy
   placeholder text **by type** (TITLE ↔ CENTERED_TITLE count as the same),
   recreate plain shapes (type, geometry, solid fill, text) and images;
2. copy the speaker notes (plain text);
3. delete the original.

Known losses, by design: character-level styling of the copied text (the
new layout's styling applies — usually what you want), shape outlines and
gradients, text auto-fit. Text whose placeholder type has no counterpart on
the target is returned in `unplaced_text` rather than dropped. Slides with
groups, tables, videos, lines, charts or word art are **refused** with the
offending element ids; the API can't recreate those on another page.

If step 2 or 3 fails, both slides stay in the deck and the error says which
one to remove. The returned `index` is 1-based (the original's position).
The tool is annotated `destructiveHint: true`.

## 6. Raw access when you need it

- `get_page(presentation, page_id)` returns any page in full with a
  `page_kind` of `slide`, `layout`, `master` or `notes`. Handy to read a
  master's theme colors. Google's raw JSON is verbose; pass `compact=True`
  for one line per element (id, type, geometry in pt, text, `placeholder`
  {type, index}) — enough to map a layout's placeholders.
- `get_presentation(presentation, fields=…)` is `presentations.get` with a
  Google field mask, e.g. `"layouts(objectId,layoutProperties)"` or
  `"slides(objectId,pageElements(objectId,shape(text)))"`. Without a mask
  the JSON is trimmed to whole slides under 200 kB and flagged
  `truncated: true`.
- `raw_request(presentation, "POST", ":batchUpdate", body=…)` sends your own
  requests — including element requests with a **layout** as
  `pageObjectId`, which is how you edit a layout's own elements.
