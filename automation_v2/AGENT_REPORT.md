# Agent Report — ui-04 Modernize travel destination presentation

## Status: IMPLEMENTATION COMPLETE (pytest blocked in-agent)

## Task completed

Modernized the Nearby travel section into clearer destination cards that distinguish the current location from available open routes, surface only view-model descriptive context, and make the primary Travel control obvious (NPC-style action strip with day cost). Form contracts, location IDs, routes, and travel behavior are unchanged. Unavailable destinations are not inferred or rendered (none are supplied by the play-scene view model).

## Deficiencies identified (before this pass)

1. Current-location card repeated a redundant invented “Current location” blurb after “You are here”.
2. Travel day cost used a falsy fallback label “Nearby” instead of always showing the supplied `dest.days` value.
3. Primary Travel buttons were full-width centered chrome without a dedicated action strip, weaker hierarchy than NPC cards.
4. Unused `.travel-destination--unavailable` CSS implied unavailable routes exist; the clarified acceptance criterion forbids inventing them when absent from the view model.

## What changed

### Template (`play_scene.html`)

- Current location card: name + “You are here” status only (no invented blurb).
- Available destination cards: name, `{{ dest.days }}d` meta, descriptive blurb from `ambience` → `environment_tags` → `tags` → `kind` (view-model fields only).
- Primary Travel button shows label + day meta; same `POST /play/{{ scene.save_id }}/travel` with `name="to_location_id"` / `value="{{ dest.location_id }}"`.
- No unavailable destination markup.

### CSS (`main.css`)

- Stronger card hierarchy aligned with NPC cards (gold current / jade available accents).
- Travel actions use inset action-strip styling; label/meta flex layout.
- Mobile (`max-width: 560px`): stacked header, padded action strip, min-height Travel control.
- Removed unused unavailable-state rules.

### Tests (`tests/test_travel_destinations_ui.py`)

- Assert hierarchy, form contract substring, days display, action label/meta, no unavailable class in template/CSS/render.
- Rendered integration check still verifies current-before-available and one submit control per destination.

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Readable destination cards/rows | Met — `travel-destination` articles in `travel-list` |
| Name + existing descriptive context | Met — `display_name` + ambience/env/tags/kind only |
| Current vs available distinguishable; unavailable neither inferred nor added | Met — `--current` / `--available` only; no unavailable markup |
| Primary travel actions easy to identify | Met — inset `travel-actions` + `travel-action-primary` |
| IDs, routes, forms, values, behavior unchanged | Met — same method/action/field/value |
| Desktop / mobile usable | Met — card CSS + 560px travel rules |
| Focused + full pytest | Blocked in-agent — orchestrator must run |
| Meaningful template/static change | Met — template + CSS changed |

## Files changed

- `src/ai_adventure/presentation/templates/play_scene.html`
- `src/ai_adventure/presentation/static/css/main.css`
- `tests/test_travel_destinations_ui.py`
- `automation/AGENT_REPORT.md`
- `automation_v2/AGENT_REPORT.md`
- `automation_v2/runs/20260728-181606-ui-04/shell_block_note.txt`

## Tests run

```text
python -m pytest -q tests/test_travel_destinations_ui.py
python -m pytest -q
```

In-agent Shell (and worktree/subagent Shell) returned `Rejected:` for every invocation. Pytest could not be executed from this session.

## Test results

Unavailable in-agent. Static review: form-contract substring, hierarchy classes, and days/`to_location_id` contracts match the updated tests.

## Remaining risks

- Orchestrator must confirm focused + full suite.
- Current location has only `current_location_name` in the scene model (no ambience); card intentionally shows status + name only.
- Unavailable / locked routes remain out of scope until the view model supplies them.

## Anything requiring human review

1. Re-run focused + full pytest after Shell is available.
2. Visual check that Travel action strips read clearly next to NPC cards.
3. Confirm no desire to expose locked routes (would need backend/view-model work outside this task).
