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

## Expansion notes

- Related: [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [BACKGROUNDS.md](BACKGROUNDS.md), [DATABASE.md](DATABASE.md), [ARCHITECTURE.md](ARCHITECTURE.md), [PLAYER_IDENTITY.md](PLAYER_IDENTITY.md).
