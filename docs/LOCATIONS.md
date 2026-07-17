# Locations (Phase 5)

## Purpose

Defines the **location substrate**: modular world content packs, authoritative location catalog, and per-save presence (mutable visit/discovery state), plus travel and location actions.

**Status:** Phase 5a–5c implemented (catalog, packs, presence, travel, **location actions**). Phase 11b adds allowlisted requirements and rewards to authored location actions. Modifier Framework **6a–6c** shipped; **6d** Event Selection Bias. Reserved `event_weight_modifiers` fields must **not** become a parallel bias path — future location auras emit generic Modifier Framework types (`weight_mult` / `chance_flat`).

Related: [WORLD_MODEL.md](WORLD_MODEL.md), [WORLD_GENERATION.md](WORLD_GENERATION.md), [EVENT_ENGINE.md](EVENT_ENGINE.md), [MODIFIER_FRAMEWORK.md](MODIFIER_FRAMEWORK.md), [DATABASE.md](DATABASE.md), [DECISIONS.md](DECISIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Confirmed principles

| Principle | Rule |
|-----------|------|
| Catalog authority | Authored pack JSON is the source of truth for what exists and how it is named. |
| Saves hold mutable state only | Presence / discovery / visit counts — not a copy of the gazetteer. |
| Display names from catalog | `current_location_name` on save/player is a denormalized cache; engine resolves from catalog on write. |
| Pack modularity | World content is organized as **regional / thematic content packs**, merged into one in-memory catalog at load. |
| Global id uniqueness | `location_id` values must be unique across all packs (fail fast at load). |
| Engine authority | Travel, explore, presence, and location requirements are engine-owned. AI never invents permanent locations. |
| Presentation ≠ mechanics | `presentation` fields (music, artwork, ambience) never affect eligibility, odds, or rewards. |

---

## Content-pack architecture (locked for Phase 5)

**Decision:** Modular packs under `data/world/packs/`, not a single flat world file.

### Why packs (not one catalog file)

1. **Scale** — Regions, sects, and homelands grow independently; one mega-file becomes unreviewable.
2. **Ownership** — A pack can later own co-located `npcs.json`, pack-local event contributions, quests, without scattering paths.
3. **Dependencies** — Packs declare `depends_on` so faction grounds (Verdant Gate) can require their geographic host (Jade Ridge).
4. **Matches existing patterns** — Same manifest → content files approach as events/story.

### Why not peer-pack everything immediately

- Empty `npcs.json` / `quests.json` stubs are noise. Pack manifests **reserve** optional content keys; only ship files that exist.
- **System catalogs stay global** for now: cultivation events remain under `data/events/` until a pack contribution loader is designed (5b+). Location packs may list optional `events` paths later; they do not replace the event engine catalog in 5a.

### Layout

```text
data/world/
  world_manifest.json          # ordered list of pack ids
  packs/
    opening_homelands/
      manifest.json
      locations.json
    jade_ridge/
      manifest.json
      locations.json
    verdant_gate/
      manifest.json            # depends_on: ["jade_ridge"]
      locations.json
```

Engine merges packs in manifest order after validating dependency closure. Callers always see one `LocationCatalog`.

---

## Location schema (catalog)

| Field | Role |
|-------|------|
| `id` | Stable permanent id |
| `kind` | `region` \| `settlement` \| `site` |
| `display_name` | Authoritative label |
| `parent_id` | Optional hierarchy parent (must exist in merged catalog) |
| `tags` | General tags (events, queries) |
| `sect_id` | Optional faction link |
| `travel` | Edge list (used in 5b; may be empty in 5a) |
| `actions` | Allowed intents flags (used in 5c; may be empty) |

### Reserved mechanical metadata (may be empty)

| Field | Future use |
|-------|------------|
| `weather_tags` | Environment / event context |
| `spiritual_density` | Cultivation / event modifiers |
| `danger_rating` | Risk gates |
| `recommended_realm` | Soft guidance / eligibility |
| `resources` | Gathering / alchemy hooks |
| `npc_spawn_tags` | NPC placement |
| `event_weight_modifiers` | Event selection tweaks |
| `cultivation_tags` | Session / ambient cultivation |
| `environment_tags` | Event `context.environment_tags` |
| `technique_tags` | Phase 6c site affinity (no migration) |
| `technique_ids` | Phase 6c site-bound technique refs (no migration) |

### Presentation metadata (never mechanical)

| Field | Role |
|-------|------|
| `music` | Audio cue key |
| `artwork` | Art asset key |
| `ambience` | Flavor / ambience key |

---

## Presence (per-save mutable state)

Table `location_presence` (migration `0008_locations`):

| Column | Role |
|--------|------|
| `save_id` + `location_id` | Unique presence row |
| `discovered_world_day` | First discovery |
| `first_visited_world_day` | First visit |
| `last_visited_world_day` | Most recent visit |
| `visit_count` | Visits recorded |

Recording a visit (character create, story relocation, free travel) upserts presence. Unknown catalog ids are rejected by the engine.

---

## Travel (Phase 5b)

Travel is a **first-class engine action**, orchestrated like cultivation sessions:

```text
PlayerIntent (travel | story relocate)
  → LocationService validation (catalog edge)
  → WorldClock.advance
  → location + presence update
  → EventService.after_story_travel (when travel-like)
  → persist + presentation
```

| Rule | Detail |
|------|--------|
| Single writer | All location changes go through `LocationService` (story + free travel). |
| Graph authority | Moves require an authored `travel` edge on the origin location. |
| Free travel | Uses edge `days`; hidden/secret routes blocked until unlock system exists. |
| Story relocate | Same edge graph; day cost from story `increment_world_day` effects (`days_override`). |
| Time-only beats | Story day advances without location change use `LocationService.advance_world_days`. |
| WorldClock | Cultivation sessions, event effects, and travel all advance `world_day` via `advance_world_days` / `SaveRepository.advance_world_day`. |

### Travel edge reserved metadata

| Field | Role |
|-------|------|
| `travel_method` | Foot, flying sword, etc. (unused in 5b) |
| `travel_danger` | Risk rating (unused) |
| `travel_restrictions` | Soft/hard blocks (fail-closed if non-empty today) |
| `travel_cost` | Money/items (fail-closed if non-empty today) |
| `visibility` | `public` \| `hidden` \| `secret` |
| `hidden_route` | Alternate hidden flag |
| `unlock_requirements` | Future unlock gates |

---

## Location actions (Phase 5c)

Locations declare which **actions** a player may attempt while present. Actions are not a separate exploration minigame — they are the verb layer for “what can I do here?”

```text
PlayerIntent (explore | inspect | …)
  → LocationService.perform_action
  → validate (catalog + location offers + gates)
  → WorldClock.advance (action duration)
  → EventEngine (after_explore / after_inspect / …)
  → persistence + presentation
```

| Piece | Role |
|-------|------|
| `data/world/action_catalog.json` | Global action definitions + reserved requirement/cost fields |
| `location.actions` | Which action ids this site offers |
| Implemented in 5c | `explore` (1 day), `inspect` (instant) |
| Catalog-reserved | cultivate, rest, talk, train, leave, travel, study, trade (`implemented: false`) |
| UI | Play scene “At this location” panel → `POST /play/{save_id}/location-action` |

Travel remains independent (`LocationService.travel` / story relocate). Cultivation sessions remain the cultivation pipeline; listing `cultivate` on a site reserves the verb for later wiring.

### Action reserved metadata

requirements, required_realm, required_technique_ids, required_items, required_reputation, cooldown_days, duration_days, stamina_cost, resource_costs, event_weight_modifiers.

### Phase 11b requirements and rewards

Allowlisted action requirements are `flags_all`, `flags_none`, `required_sect_id`, `min_sect_standing`, `min_realm_order`, and `required_location_ids`; unknown keys fail catalog validation. Rewards may adjust sect standing or money, grant items, set flags, unlock/discover locations, emit triggers, or adjust an NPC relationship. `supports_facets` is presentation metadata, while `background_money_bonus` augments an authored money reward for a matching background.

Hidden travel edges are included and usable only when all `unlock_requirements.flags_all` story flags are true. Hidden edges with no such requirements remain blocked.

---

## Phase milestones

| Milestone | Scope |
|-----------|--------|
| **5a** | Packs + catalog + validation + presence + migrate existing story/background/sect location ids |
| **5b** | Travel graph, WorldClock unification, live `after_story_travel`, story uses LocationService |
| **5c** | Location action catalog; explore + inspect; events with real `location_ids`; UI |

---

## Non-goals (Phase 5c)

- Procedural exploration / map UI / overworld
- Travel combat, fog of war, hidden regions
- Dynamic NPC schedules
- Executing reserved actions (rest/talk/train/…) beyond catalog presence
