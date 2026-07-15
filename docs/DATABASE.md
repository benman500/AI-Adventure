# Database

## Purpose

Owns persistence and data-architecture expectations for the world simulation: what must be stored, what must scale, and how AI is kept out of direct writes. This is design-level—not an implementation schema yet.

## Confirmed design

- Everything important is **persistent**.
- Engine is the **only** writer of saved state; AI never modifies saves directly.
- Must scale toward: enormous technique encyclopedia, NPC memories, world history, factions/sects, economies, relationships, instances, and vertical realms.
- **MVP implementation:** small datasets; simple save/load of core character + seed world.
- **Long-term architecture:** schemas and storage choices must not assume “only a few techniques” or “only player state matters.”

## Proposed details

### Responsibility split

| Store concerns | Examples |
|----------------|----------|
| Player profile | Name, background, path, cultivation progress, Body/Qi/Soul/Dao/Foundation Quality |
| Inventory / economy | Money, items, debts |
| Techniques | Encyclopedia records + mastery links |
| Tribulations | Templates + instance runs + outcomes |
| Heaven's Will | Attention/pressure fields |
| World | Regions, settlements, sites, instance templates |
| Agents | NPCs using **same cultivation schema** as players |
| Factions | Sects, kingdoms, standings |
| History | Durable events, object provenance |
| Time | World clock, cooldowns, calendars |

### Architectural requirements (proposed)

- Stable ids for all important entities.
- Sparse metadata allowed (techniques with empty lore fields early).
- Referential links (known users, prerequisites, faction membership) rather than duplicated prose blobs alone.
- Migrations as content and fields grow.
- Saves under `saves/` (player-facing); content databases may be separate authored datasets later.

### AI interaction with storage

```mermaid
flowchart LR
  ai[AI]
  engine[Engine]
  db[PersistentStores]
  ai -->|"drafts proposals only"| engine
  engine -->|"sole writer"| db
  db -->|"read models for prompts"| engine
  engine -->|"structured facts"| ai
```

### MVP vs architecture

| MVP implementation | Long-term architecture |
|--------------------|------------------------|
| Single local save file/document ok | Scalable DB or equivalent layered stores |
| Few tables/collections | Techniques-at-scale, memory logs, market history |
| Manual content inserts | Import pipelines + AI proposal commits |

## Out of scope / non-goals

- Picking SQL vs document vs SQLite vs cloud in this pass (unresolved).
- Writing migrations or ORM code here.

## Unresolved design questions

- Primary storage technology?
- Authored content packs vs per-save world copies?
- How to sync AI-committed techniques into shared content vs per-world uniqueness?
- Backup/export format for players?
- Compression/archival of old history/memory?

## Expansion notes

- Phase 1 should establish technique + world entity schemas even if mostly empty ([DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md)).
- Related: [TECHNIQUES.md](TECHNIQUES.md), [NPCS.md](NPCS.md), [ECONOMY.md](ECONOMY.md), [WORLD_GENERATION.md](WORLD_GENERATION.md), [AI_SYSTEM.md](AI_SYSTEM.md).
