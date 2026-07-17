# Sects

## Purpose

Owns living sects as persistent factions: hierarchy, politics, recruitment, and rivalry—aligned with serious xianxia tone.

**Status:** Phase **9d** ships player **membership lifecycle** + **institutional standing**. Full living sect simulation remains architecture.

Related: [NPCS.md](NPCS.md), [SECT_LIFE.md](SECT_LIFE.md), [REPUTATION.md](REPUTATION.md), [DECISIONS.md](DECISIONS.md), [DATABASE.md](DATABASE.md).

---

## Confirmed design

- The setting contains **sects** as a core world container.
- Themes include **sect politics**, **rivalry**, **betrayal**, ambition, and sacrifice ([GAME_VISION.md](GAME_VISION.md)).
- The world exists **without the player**; sects continue pursuing goals off-screen ([GAME_PRINCIPLES.md](GAME_PRINCIPLES.md)).
- Engine owns permanent facts about sect existence, holdings, and durable political outcomes; AI narrates.
- **Catalog authority:** pack `sects.json` defines identity, ranks, and authored standing/join parameters.
- **Saves = mutable only:** `sect_membership` (affiliation + rank) and `sect_standing` (per-sect institutional score).
- **One primary membership** per save (`UNIQUE(save_id)` on membership). Multi-sect deferred.
- **NPC membership stays separate:** catalog `sect_id` + optional `sect_id_override` — not a shared membership table.
- **Institutional standing ≠ NPC relationship ≠ reputation graph.** Three distinct systems.

---

## Phase 9d — membership lifecycle + institutional standing

### Pipeline

```text
Intent → SectService.join / standing apply → Validation → (optional WorldClock)
      → mutate membership / standing → EventEngine (optional) → Persistence → Presentation
```

Story `set_sect_membership` delegates to the same join path (may waive the standing eligibility gate; catalog ids and ranks still validate).

### Catalog (`sects.json`)

| Field | Role |
|-------|------|
| `sect_id` | Permanent catalog id |
| `display_name` | Authoritative label |
| `home_location_id` | Sect grounds location |
| `description` | Presentation |
| `ranks` | Ladder: `rank_id`, `display_name`, `order` |
| `initial_standing` | Authored standing seed applied on join (not an engine constant) |
| `min_standing_to_join` | Eligibility floor for non-waived joins (default `0`) |

### Player mutable state

| Table | Role |
|-------|------|
| `sect_membership` | One primary affiliation: `sect_id`, `rank_id`, `joined_at` |
| `sect_standing` | Per `(save_id, sect_id)`: `standing_score` (−100…100), `updated_world_day` |

Standing can exist without membership later (recruitment / post-expulsion). **First affiliation join** always seeds catalog `initial_standing` (authored probation value). Later rank changes on the same sect preserve existing standing.

### Standing mutations

- Engine **validates and clamps**; deltas come from **authored catalogs** (e.g. NPC action `sect_standing_delta`).
- No hardcoded per-sect standing numbers in engine code beyond shared clamp bounds.
- NPC `relationship_score` never substitutes for sect standing.

### Join eligibility (engine)

| Check | Rule |
|-------|------|
| Catalog | `sect_id` and `rank_id` must exist |
| Primary membership | Reject join if already member of a **different** sect |
| Standing gate | Non-waived joins require standing ≥ `min_standing_to_join` (missing standing row treated as `0`) |
| Story waive | Opening recruitment may set `waive_standing_gate=True` |

### Non-goals (Phase 9d)

- Full [REPUTATION.md](REPUTATION.md) opinion graph
- Sect Life (schedules, missions, boards, libraries)
- Multi-sect membership
- NPC membership table / Actor unification
- Sect → ModifierSnapshot sources
- AI inventing standing or ranks

---

## Long-term architecture (not 9d)

| Aspect | Contents |
|--------|----------|
| Goals | Engine-owned objectives (expand, hoard arts, crush rivals) |
| Members | NPCs with roles and loyalties (shared schema later) |
| Assets | Techniques, resources, territories, vassal ties |
| Politics | Internal halls, succession, betrayal hooks |
| External | Rivalries, alliances, tournament participation |

Daily life remains in [SECT_LIFE.md](SECT_LIFE.md). Local opinions remain in [REPUTATION.md](REPUTATION.md); institutional standing may later *feed* that graph without replacing it.

---

## Unresolved design questions

- Orthodoxy vs demonic axes—mechanical or flavor?
- Sharing of techniques inside sects vs stolen manuals?
- Kingdom vs sect authority when both exist?
- Multi-sect / guest tracks timing?

## Expansion notes

- Sects are a faction subtype; reuse faction relations for kingdoms and smaller halls.
- Related: [NPCS.md](NPCS.md), [TECHNIQUES.md](TECHNIQUES.md), [COMBAT.md](COMBAT.md), [WORLD_GENERATION.md](WORLD_GENERATION.md), [SECT_LIFE.md](SECT_LIFE.md), [REPUTATION.md](REPUTATION.md).
