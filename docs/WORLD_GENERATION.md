# World Generation

## Purpose

Owns how locations and world content are created, persisted, and expanded—authored anchors plus procedural growth—while keeping the world a continuous simulation.

## Confirmed design

- Long-term vision includes **procedural locations**, **secret realms**, **ancient inheritances**, **lower worlds**, and **higher immortal realms** ([GAME_VISION.md](GAME_VISION.md)).
- Everything important is **persistent**; generated places that matter become durable world objects.
- Engine owns permanent facts about what exists; AI may describe but must not silently spawn permanent places into saves without engine commit.
- **MVP implementation:** one tiny starting context (authored or lightly generated).
- **Long-term architecture:** generation pipelines that emit engine-valid entities (regions, settlements, sites, instances) from day-one schemas ([WORLD_MODEL.md](WORLD_MODEL.md), [DATABASE.md](DATABASE.md)).

## Proposed details

### Generation modes

| Mode | Use |
|------|-----|
| Authored anchors | Critical starter towns, major sects, unique inheritances |
| Procedural fill | Wilderness nodes, minor markets, remnant tombs |
| Instance generation | Secret realm layouts, tournament brackets as temporary instances with lasting consequences |
| Discovery commit | Player/AI-assisted finds validated then persisted |

### What generation must output

Engine entities with ids—not orphan prose. Prefer linking to techniques, NPCs, factions, and history records when relevant.

### MVP vs architecture

| MVP implementation | Long-term architecture |
|--------------------|------------------------|
| Single starting settlement/grounds | Multi-region lower worlds |
| No procedural sprawl required | Procedural locations + instance templates |
| Static map stub | Dynamic discovery and rising immortal access points |

## Out of scope / non-goals

- Shipping a continent generator in MVP.
- Infinite disposable locations with no persistence.

## Unresolved design questions

- Seed/reproducibility model for procedural content?
- How much generation happens at world-init vs on exploration?
- Secret realm reuse vs one-time collapse?
- Authored-to-procedural ratio targets per phase?

## Expansion notes

- Worldgen should call the same commit path used when AI proposes locations or inheritances.
- Related: [WORLD_MODEL.md](WORLD_MODEL.md), [SECTS.md](SECTS.md), [TECHNIQUES.md](TECHNIQUES.md), [ECONOMY.md](ECONOMY.md).
