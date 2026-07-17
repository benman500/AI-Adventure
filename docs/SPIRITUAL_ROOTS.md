# Spiritual Roots (Phase 7)

## Purpose

Defines **Spiritual Roots** as the **second Modifier Framework source**: catalog authority, per-actor ownership persistence, and emission of allowlisted effect bundles into ephemeral `ModifierSnapshot` values.

Roots do **not** invent private math channels. Sessions, breakthroughs, and event selection bias continue to read snapshots only.

Related: [MODIFIER_FRAMEWORK.md](MODIFIER_FRAMEWORK.md), [TECHNIQUES.md](TECHNIQUES.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [DECISIONS.md](DECISIONS.md), [DATABASE.md](DATABASE.md).

---

## Confirmed principles (locked)

| Principle | Rule |
|-----------|------|
| Same pipeline | Intent → Service → `ModifierSnapshot(activity)` → consumer allowlist → pure calculation → mutation |
| Source only | Roots emit `EffectInstance`s; they never mutate meters or event odds directly |
| Shared types | Roots reuse existing allowlisted effect types (`session_*`, `breakthrough_chance_flat`, `weight_mult`, `chance_flat`, `flag`) |
| Catalog authority | Root definitions live in JSON; saves hold ownership only |
| Ephemeral snapshot | Never persist aggregated modifiers |
| Boundless out | Path multipliers stay outside the framework |

---

## Architecture

```text
SpiritualRoot catalog + ownership (save)
   → spiritual_root_ownership_to_effect_instances()
   → (+ technique mastery instances)
   → ModifierEngine.aggregate(activity)
   → ModifierSnapshot
   → Sessions / Breakthroughs / Event selection bias
```

### Layer ownership

| Layer | Owns |
|-------|------|
| `data/cultivation/spiritual_roots.json` | Root identity, element tag, `effect_bundle_id` |
| Effect bundles | Parametric effects (shared with techniques) |
| `spiritual_root_ownership` table | Awakened roots per save/actor |
| Source adapter (`engine/spiritual_roots.py`) | Ownership → `EffectInstance` (`source_kind=spiritual_root`) |
| Snapshot builder (service) | Combine technique + root instances; aggregate once |
| Consumers | Unchanged allowlists; ignore foreign types |

---

## Catalog schema

```json
{
  "schema_version": 1,
  "roots": [
    {
      "id": "root_wood_steady",
      "display_name": "Steady Wood Root",
      "element": "wood",
      "grade_rank": 1,
      "effect_bundle_id": "bundle_root_wood_steady",
      "description": "A common wood-aligned root that slightly steadies practice progress."
    }
  ]
}
```

| Field | Role |
|-------|------|
| `id` | Permanent catalog id |
| `display_name` | UI label |
| `element` | Flavor / future affinity (`wood`, `fire`, `earth`, …) — not a private math channel |
| `grade_rank` | Sortable grade (MVP: 1) |
| `effect_bundle_id` | Must exist in effect bundle catalog |
| `description` | Lore / presentation |

---

## Persistence (`0010_spiritual_roots`)

| Column | Role |
|--------|------|
| `save_id` + `actor_id` + `root_id` | Unique ownership |
| `awakened` | 1 when active (rows are awakened ownership) |
| `grade_rank` | Mutable personal grade (MVP starts at catalog grade) |
| `awakened_world_day` | When the root was recorded |

Catalog is never copied into the save beyond `root_id` + mutable grade.

---

## Starter content (Phase 7)

| Root | Bundle bias |
|------|-------------|
| `root_wood_steady` | `session_progress_mult` |
| `root_fire_qi` | `session_qi_gain_mult` |
| `root_earth_attunement` | `weight_mult` category `cultivation` (event selection) |

**Character create:** every new player awakens `root_wood_steady` (proves sessions consume roots without UI friction). Additional roots may be awakened via service API / tests.

---

## Non-goals (Phase 7)

- Equipment, sect bonuses, location auras, temporary buffs
- Combat root modifiers
- Dual cultivation / root fusion / rare heavenly roots systems
- AI root generation
- Framework refactors beyond wiring a second source

---

## Testing expectations

| Layer | Tests |
|-------|--------|
| Catalog | Roots reference valid bundles; unique ids |
| Adapter | Awakened ownership → `EffectInstance` with `source_kind=spiritual_root` |
| Snapshot | Technique + root instances both appear in aggregate audit |
| Consumers | Session / breakthrough / event bias change with root equipped; still no direct catalog reads |
| Migration | `0010_spiritual_roots` creates ownership table |
| Regression | Existing cultivation / event / technique tests pass |

---

## Expansion notes

- Update [DECISIONS.md](DECISIONS.md), [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md), [MODIFIER_FRAMEWORK.md](MODIFIER_FRAMEWORK.md), [DATABASE.md](DATABASE.md) when Phase 7 ships.
- Later sources must follow the same adapter → aggregate → snapshot pattern.
