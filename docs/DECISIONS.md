# Decisions

## Purpose

Records locked implementation decisions so code and docs stay aligned. Prefer updating this file when a milestone resolves an open design question.

---

## Milestone 2 — Character creation and saves

| Decision | Choice |
|----------|--------|
| Save storage | One SQLite database (`saves/game.db`) holds **many** save worlds as rows sharing a schema. |
| Save scope | Each save eventually owns the entire persistent world for that run (player, inventory, events today; NPCs, sects, world state later). |
| Delete | Soft-delete (`deleted_at`). Permanent IDs are never reused. Explicit confirmation required. |
| Background selectable set (M2) | Data files only: **Merchant Family**, **Alchemist's Apprentice**, **Hunter**. Adding a background = add/validate a data file (no engine code change). |
| Background meaning | Pre-game **life history** stored as structured seed data—not a class, not destiny. Seeds are not simulated in M2. |
| Personality | Five universal questions. Persist **answers only**. No traits, Dao, or alignment assignment at creation. |
| Boundless Foundation | Not offered at creation. New characters start on the **ordinary** cultivation path. Story event comes later. |
| Money (M2) | Single integer field `money_copper` (mundane coin). |
| Active save | Cookie `active_save_id` after create/load. |
| IDs | UUID strings for persistent rows (`EntityMixin`). |

---

## Milestone 3 — Opening story + first cultivation loop

| Decision | Choice |
|----------|--------|
| Story engine | Data-driven JSON nodes; authoritative `story_progress.current_node_id`. |
| Anomaly trigger | First **breakthrough attempt** when qi/progress thresholds met — **not** a fixed practice-session count. |
| Anomaly presentation | Mystery / unexplained stall — not talentless or broken; investigations before Elder Yun Mei. |
| Revealer (M3) | **Elder Yun Mei**, Verdant Gate Foundation Hall — single authored NPC for this slice. |
| Boundless framing | Ancient path, openly taught once, abandoned for cost/difficulty; incomplete manuscripts; obsolete in modern doctrine. |
| Sect (M3) | **Verdant Gate Sect** (`sect_verdant_gate`) on Jade Ridge. |
| Cultivation methods | **Absorb Qi**, **Stabilize Foundation**, **Calm the Mind** — nearly identical M3 mechanics; establishes UI architecture. |
| Path lifecycle | `path_status`: `provisional` → `confirmed_ordinary` \| `confirmed_boundless`; permanent after choice. |
| World clock (M3) | `game_saves.world_day` incremented on travel story effects only. |
| M2 save bootstrap | First play load creates `story_progress` at background entry node. |
| Deferred from M3 | Profession earn, technique records, combat, full sect sim (later milestones). |
| Schema authority | **Alembic only** for production/dev DB. `create_app` must never call `create_all`. |
| Migration 0003 | **Idempotent** upgrades (skip existing columns/tables) so SQLite non-transactional DDL drift can recover. |

### Schema drift note (Milestone 3 repair)

Older builds called ``Base.metadata.create_all()`` on app startup. That created tables **without** ``alembic_version`` history. Later, stamping to ``0002`` and running ``0003`` under SQLite could apply DDL that survived even if Alembic did not record head—re-running then failed with ``duplicate column name: world_day``. Fix: remove startup ``create_all``, make ``0003`` idempotent, and keep tests on isolated temp DBs only.

---

## Expansion notes

- Related: [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [BACKGROUNDS.md](BACKGROUNDS.md), [DATABASE.md](DATABASE.md), [ARCHITECTURE.md](ARCHITECTURE.md), [PLAYER_IDENTITY.md](PLAYER_IDENTITY.md), [OPENING_STORY.md](OPENING_STORY.md).
