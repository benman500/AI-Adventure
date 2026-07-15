# Game Vision

## Purpose

Defines the high-level product intention for a persistent cultivation **world simulation** with AI narration. Authoritative philosophy lives in [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md). This document owns pitch, tone, pacing, and long-term product horizon.

## Confirmed design

### What this project is

- This is **not** simply an AI text adventure.
- It is a **persistent cultivation world simulation**: the engine permanently simulates the world; AI provides narration, dialogue, and descriptions.
- The **world exists independently of the player**.
- **Everything important is persistent.**
- The **AI never determines numerical outcomes** and **never modifies saved state**.

### Setting and systems

- The setting is a cultivation world containing **sects**, **tournaments**, **secret realms**, **professions**, **lower worlds**, and **higher immortal realms**.
- **Cultivation** and **profession** are separate. Profession earns resources, reputation, money, influence, and knowledge. Cultivation determines personal power. They support each other; neither replaces the other.
- Character **backgrounds** are **upbringing before entering cultivation**, not reincarnation and not rigid classes. They grant starting knowledge, skills, contacts, opportunities, reputation, and possessions. The player may later learn every profession.
- Early on, every player faces a **mandatory story choice** (~first 30 minutes): **get fixed and cultivate as a normal cultivator** (fully viable), or walk the **Boundless Foundation Path** (hard path—greater cost for extraordinary long-term potential). Not at creation; not destiny; Boundless is **not objectively superior**; ordinary is a first-class playthrough. NPCs may walk Boundless under the same rules ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).
- Cultivation uses locked early major realms: **Body Tempering**, **Qi Condensation**, **Foundation Establishment**, **Core Formation**, plus component systems **Body**, **Qi**, **Soul**, **Dao**, and **Foundation Quality** ([CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [REALMS.md](REALMS.md)).
- **Players and NPCs share one cultivation ruleset**—no unique player cultivation rules.
- **Tribulations** (heavenly, heart demons, mental trials, dao comprehension trials) are a **signature feature** ([TRIBULATIONS.md](TRIBULATIONS.md)).
- **Heaven's Will** balances the world by reacting to major events and powerful cultivators ([HEAVENS_WILL.md](HEAVENS_WILL.md)).
- Combat/power aggregates (e.g. CPI) are **internal only**; players never see numerical combat power.
- An **enormous permanent technique encyclopedia** is a **core feature** of the vision. MVP need not ship thousands of techniques, but architecture must support them from day one.
- The **game engine** is authoritative for statistics, inventory, money, cultivation progress, breakthroughs, combat, time, techniques as world objects, and permanent facts.
- The **first playable version** remains intentionally small, while **architecture is designed for the complete vision** from day one.

### Session length and pacing

- Target sessions are **15–60 minutes**.
- The game must also support **marathon sessions of several hours**.
- Cultivation is **long-term**.
- The player should **always feel that progress was made**, even in a short session (resources, understanding, relationships, technique study, cultivation inches—not only major breakthroughs).

### Tone and thematic content

- Tone resembles **serious xianxia cultivation novels**: serious and epic, with occasional humor that never becomes parody.
- **No parody. No fourth-wall humor.**
- Themes include: **sect politics**, **rivalry**, **betrayal**, **ancient mysteries**, **exploration**, **philosophy**, **ambition**, **sacrifice**, and **hope**.
- **Violence** exists. **Romance** may exist. **Politics** exist.
- **No excessive gore.**
- **Explicit sexual content** is optional and **player-toggleable** (toggle required; default unresolved).

### Long-term product goals (architecture must anticipate)

These are **not** MVP feature requirements, but they **must influence architectural decisions today**:

- Living sects
- Kingdoms
- Immortal realms
- Procedural locations
- NPC memories
- World history
- Tournaments
- Dynamic economies
- Auctions
- Caravans
- Professions
- Relationships
- Factions
- Trade routes
- Secret realms
- Ancient inheritances
- Immortal ascension
- Enormous technique encyclopedia (cultivation, body, weapon, movement, soul, formation, alchemy, beast, immortal, and related manuals)
- Signature tribulations (heavenly, heart demons, mental, dao trials)
- Heaven's Will world balancing
- Multi-axis cultivation (Body, Qi, Soul, Dao, Foundation Quality) on a shared player/NPC ruleset

## Proposed details

These are provisional and may change without breaking the confirmed vision.

### Product pillars

1. **World simulation first** — The world keeps existing; the player participates in it.
2. **Long-horizon growth** — Cultivation is a long arc; short sessions still leave lasting progress.
3. **Engine truth, AI texture** — Numbers and permanence live in the engine; AI narrates what the engine already resolved or knows.
4. **Background as opportunity** — Upbringing opens doors; it does not assign destiny.
5. **Profession as support** — Work funds power; work is not power itself.
6. **Vertical and lateral room** — Local grounds → sects → secret realms → immortal ascent, plus trade, politics, and technique legacy.
7. **Hard path or get fixed** — Mandatory early informed irreversible choice: ordinary (fixed) and Boundless are both full viable careers; never a chosen-one lock or creation option.
8. **Serious xianxia tone** — Gravitas, ambition, and mystery; humor is seasoning only.

### Player fantasy

You enter cultivation from a mortal upbringing—not as a reincarnated scripted savior. Early on you face an anomaly and a true choice: be **fixed** and rise as a normal cultivator among peers, or take the **hard Boundless** road for a higher distant ceiling. Both careers are real. You earn power, build professions and relationships, and leave permanent marks on a world that does not pause when you look away. Techniques and histories accumulate. Rivalries and sect politics matter. If Boundless, you may one day contest cultivators a major realm above ordinary peers—because you paid for it, not because destiny owed it to you.

### Vision-level success criteria

- Important world and character state persist and remain consistent.
- A 15–60 minute session can still yield felt progress; marathon sessions remain rewarding.
- Players trust that power and outcomes come from the engine.
- Architecture can grow into living factions, economies, techniques-at-scale, and immortal ascent without rewriting core authority rules.
- AI enriches text without becoming a second rules engine.
- Tone stays serious xianxia; explicit content respects the player toggle.

### Default assumptions (proposed)

- **Single-player**, local persistence for the early product.
- Presentation is a **text-first** interface (exact medium unresolved).
- Explicit sexual content toggle defaults to **off** until playtesting says otherwise.

## Out of scope / non-goals

- Treating the project as “chat with a dungeon master” with no simulation authority.
- Shipping the full long-term checklist inside MVP.
- Parody tone, fourth-wall comedy, or excessive gore as house style.
- Player reincarnation as the default background fantasy.
- Implementing application code in this document set.

## Unresolved design questions

- Single-player only long-term, or multiplayer later?
- Exact presentation medium (CLI, terminal UI, local web app, etc.)?
- Default value and UI placement for the explicit sexual content toggle?
- How “felt progress” in a short session is measured and surfaced in the UI?
- How strongly offline simulation advances when the player is away between sessions?

## Expansion notes

- Distinguish **MVP implementation** from **long-term architecture** in every major feature (see [MVP_SCOPE.md](MVP_SCOPE.md)).
- Related documents: [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md), [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [REALMS.md](REALMS.md), [TRIBULATIONS.md](TRIBULATIONS.md), [HEAVENS_WILL.md](HEAVENS_WILL.md), [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [BACKGROUNDS.md](BACKGROUNDS.md), [WORLD_MODEL.md](WORLD_MODEL.md), [AI_BOUNDARIES.md](AI_BOUNDARIES.md), [MVP_SCOPE.md](MVP_SCOPE.md), [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md).
