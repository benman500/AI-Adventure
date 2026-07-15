# Character Creation

## Purpose

Defines how a new character is assembled before play: identity, upbringing background, personality seeds, and starting packages. Cultivation path is **not** chosen at creation—see [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md).

## Confirmed design

- The player does **not** reincarnate. Background is **upbringing before cultivation**, not a previous life.
- Backgrounds are **not rigid classes**.
- Initial backgrounds are the ten listed in [BACKGROUNDS.md](BACKGROUNDS.md).
- Backgrounds provide starting **knowledge**, **skills**, **contacts**, **opportunities**, **reputation**, and **possessions**.
- Backgrounds **never prevent** learning other professions; the player may later learn every profession.
- Cultivation and profession are **separate systems**.
- **Path is not chosen at creation.** Characters begin on **provisional ordinary cultivation** until a mandatory early story event introduces the Boundless Foundation Path ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).
- Starting cultivation uses the **shared** multi-axis schema (Body, Qi, Soul, Dao, Foundation Quality) and locked early realms—**no unique player cultivation rules**.
- The engine is authoritative for character statistics and permanent mechanical facts created here.

## Proposed details

### Creation flow

1. **Identity** — Display name (and any later cosmetic fields once approved).
2. **Background** — Select one upbringing background (not destiny).
3. **Personality questions** — Answers seed hidden traits, dialogue tendencies, and possible Dao affinities ([PLAYER_IDENTITY.md](PLAYER_IDENTITY.md)).
4. **Starting package** — Engine applies knowledge, skills, contacts, opportunities, local reputation seeds, possessions.
5. **Profession readiness** — Empty or lightly seeded familiarity; no class lock.
6. **Technique seed (proposed)** — Optional tiny starter techniques as persistent records, if MVP includes them at creation.
7. **Enter play** — Starting context per [MVP_SCOPE.md](MVP_SCOPE.md) / [WORLD_MODEL.md](WORLD_MODEL.md); path choice arrives later via the Boundless story event.

### Conceptual character record fields (design-level)

| Field category | Examples |
|----------------|----------|
| Identity | Name |
| Origin | Background id (upbringing) |
| Cultivation | Provisional ordinary path until Boundless story event; starting realm/stage on locked early ladder |
| Axes | Body, Qi, Soul, Dao, Foundation Quality (same schema as NPCs) |
| Support | Profession progress; money; inventory |
| Social seed | Contacts, opportunities, **local** reputation seeds ([REPUTATION.md](REPUTATION.md)) |
| Identity seed | Hidden traits, dialogue tendencies, Dao affinity weights ([PLAYER_IDENTITY.md](PLAYER_IDENTITY.md)) |
| Capability seed | Knowledge flags; starting skills |
| Techniques | Learned technique ids / mastery (even if empty at start) |

Attribute generation method (fixed / budget / rolls) is not confirmed.

### Separations that must remain true

| Concept | Is | Is not |
|---------|----|--------|
| Background | Upbringing package | Class or reincarnation destiny |
| Boundless Foundation Path | Informed permanent story-event choice (later) | Creation option or protagonist-only fate |
| Profession | Earns resources, reputation, money, influence, knowledge | Personal combat power |
| Cultivation | Personal power | A profession |

## Out of scope / non-goals

- Implementing UI or save formats.
- Exclusive secret physiques that only one background can take by destiny.
- Full item lists for every background.
- Multi-character party creation.
- Boundless Foundation Path selection during creation (owned by [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).

## Unresolved design questions

- Rename, reroll, or preview packages before commit?
- Starting age, presentation, appearance customization?
- Attribute generation method?
- MVP package depth for all ten backgrounds?

## Expansion notes

- Compose creation from data packages (background + cultivation seed + optional technique seeds). Path modifiers apply only after the Boundless story event.
- Do not reintroduce reincarnation as the default origin without an explicit design reversal.
- Related documents: [BACKGROUNDS.md](BACKGROUNDS.md), [PLAYER_IDENTITY.md](PLAYER_IDENTITY.md), [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [DAO_SYSTEM.md](DAO_SYSTEM.md), [REPUTATION.md](REPUTATION.md), [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md).
