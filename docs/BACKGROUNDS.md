# Backgrounds

## Purpose

Defines character backgrounds as the player's **pre-game life history**—structured persistent seeds, not reincarnation, not rigid classes, and never a permanent profession lock.

## Confirmed design

- Background = **life before the game begins** (family, hometown, upbringing, education, occupation, contacts, obligations, opportunities, possessions, etc.).
- Background is **not a class** and does not invent destiny ([GAME_PRINCIPLES.md](GAME_PRINCIPLES.md)).
- Backgrounds are **data-driven** (`src/ai_adventure/data/backgrounds/*.json`). New backgrounds are new validated data files—no engine code change required.
- Seeds are stored on the save for later systems (NPCs, relationships, quests, reputation). Milestone 2 does **not** simulate them.
- The player may later learn **every** profession.
- Background changes **how** the player reaches the Boundless Foundation story event later—not **whether**. Path is never chosen here ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).

## Milestone 2 selectable backgrounds

| id | Display name |
|----|----------------|
| `merchant_family` | Merchant Family |
| `alchemists_apprentice` | Alchemist's Apprentice |
| `hunter` | Hunter |

## Long-term roster (content backlog)

Still planned as data files later (not all selectable in M2):

- Blacksmith's Apprentice, Scholar, Farmer, Doctor, Street Urchin, Beast Keeper, Minor Noble

(Plus the three above.)

## Seed categories (schema)

| Category | Meaning |
|----------|---------|
| History | Family/household, hometown, upbringing, education, former occupation, memories, obligations, favors |
| Reputation seeds | Local standing labels for later opinion systems |
| Relationship seeds | Future relationship graph hooks |
| Known contacts | Named contact seeds (not live NPCs in M2) |
| Opportunities | Future job/intro hooks |
| Starting knowledge | Tag list |
| Starting possessions | Item stacks |
| Starting money | Mundane copper integer |
| Intro flavor / location | Presentation + `current_location_*` |

## Hard rules

- Do not hardcode background ids into engine rule branches for ordinary creation.
- Do not treat background as combat class tiers.
- Do not expose Boundless Foundation as a background.

## Related

- [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [DECISIONS.md](DECISIONS.md), [REPUTATION.md](REPUTATION.md), [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md).
