# Game Principles

## Purpose

Defines the permanent design philosophy of this project. Other documents describe systems and scope; this document owns the rules that must not be traded away for convenience.

## Confirmed design

### Core identity

This project is **not** simply an AI text adventure.

It is a **persistent cultivation world simulation**. The game engine permanently simulates the world. The AI provides narration, dialogue, and descriptions. The world exists **independently of the player**. Everything important is **persistent**. The AI never determines numerical outcomes or modifies saved state.

### Permanent principles

1. **The world exists without the player.**  
   NPCs, factions, economies, and events continue according to engine rules whether or not the player is present or watching.

2. **Everything important is persistent.**  
   Cultivation progress, inventory, money, relationships, techniques, world history, and other consequential facts survive across sessions and are not washed away for narrative convenience.

3. **AI narrates; the engine decides.**  
   The engine owns statistics, outcomes, time, and permanent facts. AI colors what already happened or what the engine already knows. AI never decides numerical outcomes and never writes saves.

4. **Cultivation is earned.**  
   Power comes from time, resources, risk, and choice—not from destined protagonist status or narrator fiat.

5. **Actions have permanent consequences.**  
   Betrayals, alliances, failures, breakthroughs, and reputational acts leave durable traces in simulation state.

6. **Background creates opportunities, not destiny.**  
   Upbringing seeds knowledge, skills, contacts, reputation, possessions, and chances. It is not a class and does not trap the player’s future professions or path.

7. **Every NPC has goals.**  
   Important characters pursue engine-owned motivations. They are not pure stage dressing for the player’s scene.

8. **Every important object has history.**  
   Techniques, inheritances, places, and relics carry provenance—creator, past owners, events—as durable world data when they matter.

9. **Long-term consistency is more important than short-term spectacle.**  
   Prefer rules and data that stay coherent over years of simulated time and many play sessions. Do not break architecture for a one-off set piece.

10. **MVP is small; architecture is large.**  
    The first playable build stays intentionally thin. Day-one data models and module boundaries must still anticipate the full vision (techniques, living world, factions, economies, ascension).

11. **Profession supports cultivation; neither replaces the other.**  
    Profession earns resources, reputation, money, influence, and knowledge. Cultivation determines personal power.

12. **Hard path or get fixed—both are viable.**  
    The Boundless Foundation choice is introduced via a **mandatory early story event** (not creation). Players may **get fixed** and play a full, satisfying **ordinary cultivator** career, or take the **hard Boundless Foundation Path**. Boundless is **not objectively superior** or destined; ordinary is **not** a consolation prize. See [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md).

13. **One cultivation ruleset for all actors.**  
    Players and NPCs use exactly the same cultivation, breakthrough, tribulation, and power systems. The player never receives unique cultivation rules—only different state and choices.

14. **Hide spreadsheet power; show cultivation fiction.**  
    Internal balance tools (such as Combat Power Index) must not be shown to players as numerical combat power. Present realm, stage, qualitative foundation, and consequences instead.

15. **Tribulations are signature.**  
    Heavenly tribulations, heart demons, mental trials, and dao comprehension trials are core fantasy—not optional garnish.

16. **Heaven's Will balances the world.**  
    The simulation reacts to major events and powerful cultivators through shared world rules, not protagonist immunity or persecution exceptions.

## Proposed details

- Treat these principles as acceptance tests for future design and code reviews: if a feature violates them, redesign the feature.
- When AI proposes new permanent content (for example a technique), the **engine commits** it as a world object after validation; AI prose alone is never the store of truth.
- Multi-axis cultivation (Body, Qi, Soul, Dao, Foundation Quality) applies to every cultivator under the same definitions ([CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md)).

## Out of scope / non-goals

- Replacing system design docs ([CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [WORLD_MODEL.md](WORLD_MODEL.md), etc.).
- Specifying implementation language or file formats.
- Softening principles for early prototypes (prototypes may omit systems; they must not contradict these rules where systems exist).

## Unresolved design questions

- Exact validation pipeline when AI proposes techniques or other permanent objects (manual review, rule filters, rarity gates)?
- How aggressively the off-screen world advances during short vs marathon sessions?

## Expansion notes

- New systems should cite which principles they uphold.
- Related documents: [GAME_VISION.md](GAME_VISION.md), [AI_BOUNDARIES.md](AI_BOUNDARIES.md), [MVP_SCOPE.md](MVP_SCOPE.md), [WORLD_MODEL.md](WORLD_MODEL.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md), [TRIBULATIONS.md](TRIBULATIONS.md), [HEAVENS_WILL.md](HEAVENS_WILL.md).
