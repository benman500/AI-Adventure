# NPCs

## Purpose

Owns non-player characters as persistent, authored world entities—not disposable dialogue props.

**Status:** Phase **9a–9d** foundation + Phase **10** authored interaction framework. Teaching (`request_instruction`) is the first proof of the generic pipeline.

Related: [SECTS.md](SECTS.md), [LOCATIONS.md](LOCATIONS.md), [TECHNIQUES.md](TECHNIQUES.md), [REPUTATION.md](REPUTATION.md), [DECISIONS.md](DECISIONS.md), [DATABASE.md](DATABASE.md), [AI_BOUNDARIES.md](AI_BOUNDARIES.md).

---

## Confirmed design (Phase 9–10)

| Rule | Detail |
|------|--------|
| Catalog authority | Pack `npcs.json` defines identity, roles, home/default locations, optional sect, cultivation **summary** |
| Saves = mutable only | `npc_world_state` stores location, status, discovered/met, relationship, flags, last interaction day |
| Stable ids | Catalog `npc_id` is permanent content id; save row UUID is the opaque `actor_id` for that instance |
| Story spawn | `spawn_npc` payload is `{ "npc_id": "…" }` only — no embedded display names |
| AI | May narrate; never invents NPC ids, standing, unlocks, or mechanical outcomes |
| Modifier Framework | Unchanged; NPCs are **not** a modifier source |
| Sect affiliation | NPC: catalog `sect_id` + optional override. Player: `sect_membership` + `sect_standing` ([SECTS.md](SECTS.md)) |
| Interactions | Permanent authored catalog (`npc_action_catalog.json`); one validation + reward pipeline for all verbs |

---

## Authored interaction framework (Phase 10)

Canonical entry: ``NpcService.interact(save_id, npc_id, action_id)``.

```text
Intent → NpcService → engine validation (requirements)
      → WorldClock (if duration_days > 0)
      → apply allowlisted rewards (same session)
      → EventEngine (if emit_trigger)
      → Persistence → Presentation
```

No interaction may bypass `NpcService`. Technique grants must go through `TechniqueService` (session-scoped learn). Catalog data never executes arbitrary code.

### Catalog (`data/world/npc_action_catalog.json`)

Each action is an authored interaction template:

| Field | Role |
|-------|------|
| `id` | Stable action id (catalog-driven; not a hard-coded three-verb enum) |
| `label` / `description` | UI |
| `duration_days` | WorldClock cost |
| `marks_met` | Marks NPC as met when true |
| `requirements` | Allowlisted gates (see below) |
| `rewards` | Allowlisted mutations (see below) |
| `presentation_template` | Placeholder narration |

Offer binding (who may show/run the action) lives in `requirements.allowed_npc_ids` and/or `requirements.required_role_tags_any`. Empty = available to all colocated NPCs (subject to other gates at execute time).

### Requirements (allowlisted)

| Field | Meaning |
|-------|---------|
| `min_relationship` | Player↔NPC relationship floor |
| `min_sect_standing` | Standing with the NPC's effective sect |
| `min_sect_standing_by_role` | Role-conditional standing floors (max matching) |
| `required_sect_id` | Player must be a member of this sect |
| `required_sect_rank_ids` | Player rank must be one of these |
| `required_realm_ids` | Player realm id allowlist |
| `min_realm_order` | Player realm order floor |
| `required_stage_ids` | Player stage id allowlist |
| `required_location_ids` | Player must be at one of these locations |
| `flags_all` | Story flags that must be true |
| `flags_none` | Story flags that must be false (claim / already-done) |
| `required_role_tags_any` | NPC must have at least one listed role tag |
| `allowed_npc_ids` | NPC id allowlist for this action |

Colocation + active/discovered remain engine invariants.

### Rewards (allowlisted — implemented)

| Type | Effect |
|------|--------|
| `adjust_relationship` | `{ "delta": int }` |
| `adjust_sect_standing` | `{ "delta": int }` — NPC's effective sect only |
| `learn_technique` | `{ "technique_id": "…" }` via TechniqueService |
| `set_flag` | `{ "flag": "…", "value": bool }` on story flags |
| `grant_item` | `{ "item_code": "…", "quantity": int }` inventory stack |
| `emit_trigger` | `{ "trigger_kind": "…" }` EventEngine hook |
| `unlock_location` | `{ "location_id": "…" }` story unlock flag + location discovery |

### Reserved reward types (not implemented)

Catalog validation **rejects** these if authored today (extension points only):

`unlock_dialogue`, `start_story`, `grant_reputation`, `modify_modifier_source`, `begin_mission`

### Shipped interactions

| Action | Role |
|--------|------|
| `inspect` | Observe; small relationship reward |
| `greet` | Greeting; relationship + optional standing |
| `ask_guidance` | Counsel; time cost; elder standing gate |
| `request_instruction` | Phase 10 vertical slice — Pei teaches `tech_foundation_guard` |
| `acknowledge_path` | Phase 11a — Yun Mei records the player's path choice |
| `request_recommendation` | Phase 11a — Yun Mei grants recommendation flag |

### Vertical slice (Phase 10)

1. Meet Instructor Pei at the cultivation hall.
2. Build relationship and Verdant Gate standing (greet / ask_guidance).
3. **Request Instruction** when gates pass.
4. Engine validates requirements; advances 1 day; teaches technique; sets claim flag; may emit event.
5. Save/reload preserves mastery + flag; duplicate request fails clearly.

### Phase 11a living-loop content (aspirations)

Post-Boundless players pursue authored north stars ([ASPIRATIONS.md](ASPIRATIONS.md)). Interactions write facts; aspirations only read them:

| Interaction | Fact written |
|-------------|----------------|
| `acknowledge_path` | `yun_mei_acknowledged_path` |
| `request_instruction` | technique + `taught_foundation_guard_pei` |
| `request_recommendation` | `elder_recommendation_yun_mei` |

---

## Content packs

```text
data/world/packs/<pack>/
  manifest.json
  locations.json
  npcs.json
  sects.json
```

---

## Mutable save state (`npc_world_state`)

Unchanged from Phase 9b. Claim markers for interactions use **story flags**, not NPC state flags, in Phase 10.

---

## Non-goals (Phase 10)

- Free-form AI dialogue
- Procedural quests / journals
- NPC schedules / shops / combat
- Sect missions / rank auto-promotion
- Reputation graph
- New modifier sources
- Reserved reward types above
- Unrestricted scripting

---

## Expansion notes

- Future verbs (Accept Trial, Receive Gift, Join Sect, …) are new catalog rows on the same pipeline.
- Later: per-NPC offer overlays if global actions + binding prove too coarse.
