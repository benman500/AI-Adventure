# Aspirations

## Purpose

Owns **long-term player purpose**: authored north stars whose eligibility is derived from durable facts other systems already write.

**Status:** Phase **11a** — catalog, read-only eligibility, Working Toward / Current Gaps on the play scene.

Related: [EVENT_ENGINE.md](EVENT_ENGINE.md), [PLAYER_IDENTITY.md](PLAYER_IDENTITY.md), [NPCS.md](NPCS.md), [SECTS.md](SECTS.md), [DECISIONS.md](DECISIONS.md), [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md).

---

## Locked laws (project triad)

| Layer | Feeling | Rule |
|-------|---------|------|
| **Aspiration** | Purpose | Direction and eligibility only |
| **Event** | Curiosity | Authored surprise; never steals the north star |
| **Identity** | Who I’ve become | Read-only presentation of facts (separate from this doc) |

Hard rules:

1. **Gameplay systems write facts.** Standing, relationships, techniques, flags, items, realm, discovery — never “quest steps.”
2. **Aspirations only read facts.** No dice rolls, no daily counters, no parallel grind meters.
3. **Catalogs are content authority.** Adding an aspiration = data (+ tests), not engine branches per id.
4. **AI never owns mechanics** or aspiration eligibility.

---

## Confirmed design (Phase 11a)

### What an aspiration is

An **aspiration** is an authored long-term goal with named **progress facets**. Each facet is an eligibility check over existing facts. When all facets are met, the aspiration is **fulfilled**.

It is **not**:

- A quest journal of ordered steps
- An MMO daily / weekly board
- A reputation graph
- A system that mutates world state

### Pipeline

```text
Facts (sects, NPCs, techniques, story flags, …)
   ↓
AspirationEngine.evaluate (pure)
   ↓
AspirationService → presentation cards
   ↓
Play UI: Working Toward / Current Gaps
```

### Catalog (`data/aspirations/aspirations.json`)

| Field | Role |
|-------|------|
| `id` | Permanent content id |
| `display_name` / `summary` / `fantasy` | Player-facing fiction |
| `kind` | `primary` (spine) or `optional` |
| `sort_order` | Spine order among primaries |
| `available_when` | Facet-style gates to show / consider |
| `requires_aspiration_ids` | Prior aspirations must already be fulfilled |
| `facets[]` | Named gaps: `id`, `label`, `description`, `hint`, `requirements` |

### Facet requirements (allowlisted readers)

| Field | Reads |
|-------|--------|
| `flags_all` / `flags_none` | Story flags |
| `path_status_any` | `players.path_status` |
| `min_sect_standing` / `required_sect_id` | Institutional standing |
| `min_npc_relationship` | `{ npc_id, min }` against `npc_world_state` |
| `known_technique_ids_any` / `_all` | Technique mastery |
| `min_foundation_stability` | Cultivation meter |
| `min_realm_order` | Realm ladder order |
| `discovered_location_ids_any` | Location presence |

### Save state

**None for 11a.** Eligibility and fulfillment are derived every read. No aspiration table.

### UI (11a)

When path is confirmed (`confirmed_ordinary` \| `confirmed_boundless`):

- **Working Toward** — current primary aspiration (first available primary that is not yet fulfilled)
- **Current Gaps** — unmet facets with fiction + hint (instruments, not checkboxes as the goal)
- Fulfilled primaries unlock the next primary via `requires_aspiration_ids`

### Seed content (11a–11b)

| Aspiration | Fantasy |
|------------|---------|
| `asp_stabilize_outer_probation` | After the anomaly, prove you belong as an outer disciple |
| `asp_earn_elder_recommendation` | Earn Elder Yun Mei’s formal recommendation (next north star) |

Instruments that close facets (11b) reuse existing writers: NPC interactions, location-action duties/jobs, travel unlocks, cultivation — not new progression systems.

| Instrument | Facts written | Facets supported |
|------------|---------------|------------------|
| Herb Path Assistance | standing, herbs, steward relationship | institutional_favor |
| Lecture Attendance | standing, Pei relationship | institutional_favor |
| Outer Grounds Chore | standing, money | institutional_favor |
| Sort Herbs (job) | money (+ alchemist bonus), herbs, standing | institutional_favor |
| Ask About Misty Path | unlock flag + presence | discovery / exploration payoff |

---

## Non-goals (11a–11b)

- Duty currency / daily streaks / profession XP
- Quest journals, claim buttons that invent progress
- Events selecting aspirations
- Identity phrase catalog (separate thin presentation work)
- Combat, AI arcs, Sect Life simulation ticks

---

## Expansion notes

- Optional aspirations are adopted by availability + player attention; do not dump twelve simultaneous north stars.
- Ordinary vs Boundless should fork **thresholds in catalog data**, not separate architectures.
- Related decisions: [DECISIONS.md](DECISIONS.md), roadmap Phase 11 Living Loop.
