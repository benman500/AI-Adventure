# Database

## Purpose

Owns persistence expectations for the world simulation: what must be stored, how saves scale, and how AI is kept out of direct writes.

## Confirmed design

- Everything important is **persistent**.
- The engine (via services/repositories) is the **only** writer of saved state; AI never modifies saves directly.
- **SQLite** + **SQLAlchemy 2** + **Alembic** ([TECH_STACK.md](TECH_STACK.md)).
- **One database file** holds **many** save worlds as rows. Each save eventually owns that run's entire persistent world ([DECISIONS.md](DECISIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md)).
- Permanent **UUID** string ids for important entities; never reuse ids after soft-delete.
- **Schema evolves only via Alembic.** Production app startup does **not** call ``Base.metadata.create_all``. Isolated tests may use ``create_all`` deliberately (see `tests/conftest_helpers.py`).
- If a local ``saves/game.db`` was created by an older ``create_all`` path and lacks ``alembic_version`` history, reconcile only after verifying the live schema matches the stamped revision (do not stamp blindly).
- Migration ``0003_opening_story_cultivation`` is **idempotent** (skips existing columns/tables). Safe when SQLite non-transactional DDL left a partial apply without updating ``alembic_version``.
- **Root cause of historical drift:** app startup formerly called ``create_all``, creating M1/M2 tables without Alembic history. After ``stamp 0002``, ``upgrade`` of 0003 applied DDL; SQLite committed those ALTERs independently of ``alembic_version``. A later re-run then hit ``duplicate column name: world_day``. Production startup no longer creates schema; use ``alembic upgrade head``.

## Milestone 2 schema

| Table | Role |
|-------|------|
| `meta_records` | Scaffold key/value marker |
| `game_saves` | Save metadata: name, background, dates, location, playtime, `deleted_at` |
| `players` | Player for a save: money, cultivation seed columns, identity answers JSON, background history JSON |
| `inventory_items` | Starting / owned item stacks |
| `event_log` | Append-only events (`character_created`, …) |

Migrations: `0001_initial`, `0002_character_saves`, `0003_opening_story_cultivation`, `0004_cultivation_phase1_meters`, `0005_cultivation_sessions`, `0006_cultivation_breakthroughs`, `0007_event_engine`, `0008_locations`, `0009_technique_mastery`, `0010_spiritual_roots`, `0011_alchemy_recipe_ownership`, `0012_npc_world_state`, `0013_sect_standing`.

### Phase 1 cultivation schema additions

| Column | Role |
|--------|------|
| `players.realm_comprehension` | 0–100 realm understanding meter |
| `players.foundation_stability` | 0–100 foundation stability meter |
| Data migration | `stage_id` `mid` → `middle` |

### Phase 2 cultivation session schema additions

| Column | Role |
|--------|------|
| `players.last_cultivation_result_json` | Structured result of the most recent active session |
| `players.cultivation_rng_counter` | Deterministic RNG counter for session rolls |
| Data migration | `realm_id` `qi_condensation` → `qi_gathering` |

### Phase 3 breakthrough schema additions

| Column | Role |
|--------|------|
| `players.breakthrough_attempts_current_stage` | Failed attempts on the current stage (resets on success) |
| `players.last_breakthrough_result_json` | Structured last breakthrough outcome |

### Phase 4a event engine schema additions

| Table / column | Role |
|----------------|------|
| `players.actor_id` | Opaque actor UUID (backfilled from `players.id`; unique). Future NPCs use their own ids as actor ids. |
| `game_saves.world_rng_counter` | Deterministic RNG stream for world events (separate from cultivation RNG). |
| `event_cooldowns` | Mutable cooldown / fire-count state per `(save, template, subject_actor)`. History stays in `event_log`. |

### Phase 5a location presence schema additions

| Table / column | Role |
|----------------|------|
| `location_presence` | Per-save mutable discovery / visit state for catalog `location_id` values. Catalog remains authoritative for existence and display names. |

Authored location definitions live in modular packs under `src/ai_adventure/data/world/` — not duplicated as DB gazetteer rows. See [LOCATIONS.md](LOCATIONS.md).

### Phase 6c technique mastery schema additions

| Table / column | Role |
|----------------|------|
| `technique_mastery` | Per-save / actor known, equipped, mastery rank/progress, learned world day. Technique catalog + effect bundles remain content authority. |

Technique definitions live under `src/ai_adventure/data/techniques/`. Mechanical effects flow through [MODIFIER_FRAMEWORK.md](MODIFIER_FRAMEWORK.md).

### Phase 7 spiritual root ownership schema additions

| Table / column | Role |
|----------------|------|
| `spiritual_root_ownership` | Per-save / actor awakened roots + grade. Root catalog + effect bundles remain content authority. |

Root definitions live under `src/ai_adventure/data/cultivation/spiritual_roots.json`. See [SPIRITUAL_ROOTS.md](SPIRITUAL_ROOTS.md).

### Phase 9b NPC world state schema additions

| Table / column | Role |
|----------------|------|
| `npc_world_state` | Per-save mutable NPC instance: `npc_id` (catalog ref), location, status, discovered/met, relationship_score, optional sect override, flags, last interaction day. Row `id` = opaque actor_id. |

NPC/sect definitions live in world packs (`npcs.json` / `sects.json`). Legacy `npc_records` is superseded for new writes. See [NPCS.md](NPCS.md).

### Phase 9d sect standing schema additions

| Table / column | Role |
|----------------|------|
| `sect_standing` | Per-save institutional standing with a catalog `sect_id`: `standing_score` (−100…100), `updated_world_day`. Unique `(save_id, sect_id)`. Separate from `sect_membership` and from NPC `relationship_score`. |

See [SECTS.md](SECTS.md).

### Milestone 3 schema additions

| Table / column | Role |
|----------------|------|
| `story_progress` | Authoritative `current_node_id`, `flags_json` per save |
| `sect_membership` | Sect id + rank for the run |
| `npc_records` | Spawned authored NPC instances per save |
| `game_saves.world_day`, `story_started_at` | Minimal world clock + opening timestamp |
| `players.dao` | Fifth cultivation axis seed |
| `players.path_status` | `provisional`, `confirmed_ordinary`, `confirmed_boundless` |
| `players.qi_reserve_*`, `cultivation_progress`, `practice_sessions` | Opening cultivation loop |
| `players.anomaly_state`, `breakthrough_readiness`, `path_confirmed_at` | Anomaly + path commit |

See [OPENING_STORY.md](OPENING_STORY.md) for story-state semantics.

### Save metadata fields

- save id (UUID)
- character name
- background id + display name
- creation date
- last played date
- current location id/name
- playtime seconds
- soft-delete timestamp

### Expansion expectation

Later tables (NPCs, relationships, sects, cities, quests, world state, cultivation progress detail, reputation edges, etc.) attach with `save_id` foreign keys. Do not redesign around a single-player-only blob.

## AI interaction with storage

```mermaid
flowchart LR
  ai[AI]
  engine[Engine]
  db[PersistentStores]
  ai -->|"drafts proposals only"| engine
  engine -->|"sole writer via repos"| db
  db -->|"read models for prompts"| engine
  engine -->|"structured facts"| ai
```

## Related

- [DECISIONS.md](DECISIONS.md), [ARCHITECTURE.md](ARCHITECTURE.md), [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [TECH_STACK.md](TECH_STACK.md).
