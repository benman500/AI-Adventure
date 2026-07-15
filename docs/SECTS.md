# Sects

## Purpose

Owns living sects as persistent factions: hierarchy, politics, recruitment, and rivalry—aligned with serious xianxia tone.

## Confirmed design

- The setting contains **sects** as a core world container.
- Themes include **sect politics**, **rivalry**, **betrayal**, ambition, and sacrifice ([GAME_VISION.md](GAME_VISION.md)).
- The world exists **without the player**; sects continue pursuing goals off-screen ([GAME_PRINCIPLES.md](GAME_PRINCIPLES.md)).
- Engine owns permanent facts about sect existence, holdings, and durable political outcomes; AI narrates.
- **MVP implementation:** full living sect simulation is not required.
- **Long-term architecture:** sects, kingdoms, and factions must be first-class entities with goals and history hooks from day one ([WORLD_MODEL.md](WORLD_MODEL.md)).

## Proposed details

### Sect as entity (proposed)

| Aspect | Contents |
|--------|----------|
| Identity | Name, grounds, ranks, banner/reputation |
| Goals | Engine-owned objectives (expand, hoard arts, crush rivals) |
| Members | NPCs with roles and loyalties |
| Assets | Techniques, resources, territories, vassal ties |
| Politics | Internal halls, succession, betrayal hooks |
| External | Rivalries, alliances, tournament participation |

### Player relationship patterns (proposed)

- Outer/inner disciple tracks, guest elder sponsorship, expulsion, defection.
- Background may ease introductions (e.g. Minor Noble) but never destinies a “sect protagonist only” arc.

### MVP vs architecture

| MVP implementation | Long-term architecture |
|--------------------|------------------------|
| Zero or one named stub faction | Living multi-sect politics |
| No full recruitment sim | Recruitment, missions, betrayal, succession |
| Static rumor text | Off-screen wars, mergers, collapses |

## Out of scope / non-goals

- Naming a full continent of sects in this document.
- Implementing politics code here.

## Unresolved design questions

- How early can the player join a sect?
- Orthodoxy vs demonic axes—mechanical or flavor?
- Sharing of techniques inside sects vs stolen manuals?
- Kingdom vs sect authority when both exist?

## Expansion notes

- Sects are a faction subtype; reuse faction relations for kingdoms and smaller halls.
- Related: [NPCS.md](NPCS.md), [TECHNIQUES.md](TECHNIQUES.md), [COMBAT.md](COMBAT.md), [WORLD_GENERATION.md](WORLD_GENERATION.md), [SECT_LIFE.md](SECT_LIFE.md), [REPUTATION.md](REPUTATION.md).
