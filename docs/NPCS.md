# NPCs

## Purpose

Owns non-player characters as persistent, authored world entities—not disposable dialogue props.

**Status:** Phase **9a–9b vertical slice** shipped: pack-local NPC catalogs, `npc_world_state` mutable save rows, story spawn by `npc_id`, one deterministic interaction (`greet`), relationship score, presentation from catalog + save.

Related: [SECTS.md](SECTS.md), [LOCATIONS.md](LOCATIONS.md), [WORLD_MODEL.md](WORLD_MODEL.md), [REPUTATION.md](REPUTATION.md), [DECISIONS.md](DECISIONS.md), [DATABASE.md](DATABASE.md), [AI_BOUNDARIES.md](AI_BOUNDARIES.md).

---

## Confirmed design (Phase 9)

| Rule | Detail |
|------|--------|
| Catalog authority | Pack `npcs.json` defines identity, roles, home/default locations, optional sect, cultivation **summary** |
| Saves = mutable only | `npc_world_state` stores location, status, discovered/met, relationship, flags, last interaction day |
| Stable ids | Catalog `npc_id` is permanent content id; save row UUID is the opaque `actor_id` for that instance |
| Story spawn | `spawn_npc` payload is `{ "npc_id": "…" }` only — no embedded display names |
| AI | May narrate; never invents NPC ids, standing, or mechanical outcomes |
| Modifier Framework | Unchanged; NPCs are **not** a modifier source in Phase 9 |
| Player Actor migration | Not required; NPCs use instance UUID as `actor_id` without shared cultivation Actor ORM |

Long-term vision (goals, memories, full cultivation parity, schedules) remains architecture — not implemented in 9b.

---

## Content packs

NPCs live in world packs (same merge rules as locations):

```text
data/world/packs/<pack>/
  manifest.json          # optional content_files.npcs
  locations.json
  npcs.json              # optional
  sects.json             # optional
```

Global uniqueness of `npc_id` across packs. Location and sect references must resolve in the merged catalogs. Pack `depends_on` must be satisfied before load.

---

## Catalog schema

| Field | Role |
|-------|------|
| `npc_id` | Permanent catalog id |
| `display_name` | Authoritative label |
| `role_tags` | e.g. `elder`, `disciple`, `teacher`, `rival`, `merchant` |
| `home_location_id` | Catalog location |
| `default_location_id` | Initial `current_location_id` on spawn |
| `sect_id` | Optional; must exist in sect catalog |
| `cultivation_summary` | `realm_id`, `stage_id`, `path_tags` — summary only, not full sim |
| `description` | Presentation |

---

## Mutable save state (`npc_world_state`)

| Column | Role |
|--------|------|
| `id` | UUID PK = opaque `actor_id` for this save instance |
| `save_id` + `npc_id` | Unique ownership of catalog NPC in a save |
| `current_location_id` | Where they are |
| `status` | `active` \| `dead` \| `absent` |
| `discovered` / `met` | Player awareness |
| `relationship_score` | Bounded int (−100…100); single facet for 9b |
| `sect_id_override` | Nullable; null → use catalog `sect_id` |
| `state_flags_json` | Small allowlisted flag map (not free scripting) |
| `last_interaction_world_day` | Last greet / interact day |

Legacy `npc_records` (display_name/role on save) is superseded; do not write new rows there.

---

## Vertical slice (9b)

1. Story ensures world state for `npc_id` (catalog lookup).
2. At matching location, player may **greet**.
3. Engine applies deterministic relationship delta; marks `met`.
4. UI shows catalog name + save relationship/met state.
5. Save/reload preserves mutable fields.

---

## Non-goals (Phase 9b)

- AI dialogue, free-form chat
- NPC cultivation simulation
- Schedules / off-screen ticks
- Combat opponents
- Full reputation opinion graph
- Additional ModifierSnapshot sources
- Expanded interaction set (Phase 9c)

---

## Expansion notes

- Phase **9c**: more interactions (`inspect`, `ask_guidance`), Event Engine hooks.
- Phase **9d**: sect standing / join eligibility.
- Later: NPC → ModifierSnapshot actors via instance `actor_id`.
