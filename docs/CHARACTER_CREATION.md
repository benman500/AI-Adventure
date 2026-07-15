# Character Creation

## Purpose

Defines how a new character is assembled before play: identity, pre-game life history (background), personality answers, and persistent starting state. Cultivation path is **not** chosen at creation—see [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md).

## Confirmed design

- The player does **not** reincarnate. Background is **life before the game begins**—structured history seeds, not a previous life and **not a class**.
- Backgrounds are **data-driven** content files. Adding a selectable background does **not** require engine code changes ([DECISIONS.md](DECISIONS.md)).
- Backgrounds **never prevent** learning other professions later.
- Cultivation and profession are **separate systems**.
- **Path is not chosen at creation.** Every new character begins on the **ordinary** cultivation path. The Boundless Foundation Path is introduced later by a mandatory story event ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).
- Starting cultivation uses the **shared** multi-axis schema and locked early realms—**no unique player cultivation rules**. No cultivation simulation runs at creation.
- Personality: five universal questions; the engine **stores answers only**. It does **not** assign permanent traits, Dao, or alignment at creation ([PLAYER_IDENTITY.md](PLAYER_IDENTITY.md)).
- The engine is authoritative for validated starting facts written into the save.

## Milestone 2 flow

1. **Name** — Display name.
2. **Background** — Select one data-driven life-history package.
3. **Personality questions** — Five answers persisted raw.
4. **Persist** — Save metadata, player row, inventory, background history JSON seeds, identity answers JSON, `character_created` event.
5. **Enter status screen** — No opening story / gameplay loop yet.

### What a background stores (seeds, not simulation)

Structured persistent seed data copied into the save, including categories such as:

- family / household, hometown, upbringing, education, former occupation
- memories, obligations, favors
- reputation seeds, relationship seeds, known contacts, opportunities
- starting knowledge, starting possessions, starting money
- introductory flavor text and starting location

Milestone 2 **does not** turn these into live NPCs, quests, or world simulation. Later milestones may.

## Separations that must remain true

| Concept | Is | Is not |
|---------|----|--------|
| Background | Pre-game life history seeds | Class, destiny, or Boundless path |
| Boundless Foundation Path | Later informed story-event choice | Creation option |
| Personality answers | Stored raw for future interpretation | Instant traits / Dao / alignment |

## Out of scope / non-goals

- Boundless Foundation selection during creation.
- Trait/Dao assignment from personality answers (later systems).
- Cultivation / combat / sect / NPC simulation at creation.

## Related

- [BACKGROUNDS.md](BACKGROUNDS.md), [PLAYER_IDENTITY.md](PLAYER_IDENTITY.md), [DECISIONS.md](DECISIONS.md), [DATABASE.md](DATABASE.md), [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md).
