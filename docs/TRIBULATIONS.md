# Tribulations

## Purpose

Defines tribulations as a **signature feature** of the game: types, when they trigger, outcome linkage to breakthroughs and Foundation Quality, uniqueness, and equal application to players and NPCs.

---

## Confirmed design

- Tribulations are a **signature pillar**, not optional flavor text.
- Major breakthroughs support **unique tribulations** among other outcomes ([CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md)).
- Include, where appropriate:
  - **Heavenly tribulations**
  - **Heart demons**
  - **Mental trials**
  - **Dao comprehension trials**
- Outcomes are **engine-authoritative**; AI narrates, never rolls success in secret.
- **Players and NPCs use the same tribulation systems.** No player-only mercy rules or exclusive trial types by default.
- Boundless Foundation Path faces **much harder** tribulations (same system, harsher parameters).
- Presentation stays serious xianxia; no parody; violence allowed without excessive gore ([GAME_VISION.md](GAME_VISION.md)).

---

## Proposed details

### Tribulation families

| Family | Typical focus | Hooks |
|--------|---------------|-------|
| Heavenly | External ordeal (lightning, pressure, world rejection) | Major realm crossings; Heaven's Will spikes |
| Heart demon | Inner contradiction, desire, guilt, ambition | Failed vows, betrayal memories, Dao instability |
| Mental trial | Will, clarity, fear, illusion | Soul axis; secret realms; inheritances |
| Dao comprehension trial | Understanding of a law/path under stress | Dao axis; technique evolution; insight breakthroughs |

A single breakthrough may chain or combine families (proposed).

### Instance model

**Proposal:** Each tribulation run is an **instance record**: template id, target actor id, triggers, severity, modifiers (path, Foundation Quality, Heaven's Will attention), resolved outcome enum, history write.

Unique tribulations = template + seeded modifiers + optional rare script—not a second player-only storyline engine.

### Link to breakthrough outcomes

| Breakthrough result | Tribulation relation (proposed) |
|---------------------|----------------------------------|
| Success | Trial cleared at required threshold |
| Failure | Trial failed; no realm advance; scars/costs possible |
| Partial success | Trial incomplete; deferred or lesser advance |
| Damaged foundations | Trial “won” or survived at cost to Foundation Quality |
| Unique tribulation | Rare template selected by engine (Heaven's Will, Dao, crimes, fortune) |

### Signature fantasy

- Visible world reaction (storm signs, sect sensors) without showing CPI.
- Heart demons that reference **persistent** memories/goals ([NPCS.md](NPCS.md) / player history).
- Dao trials that can alter Dao axis and technique comprehension.

### MVP vs architecture

| MVP | Long-term |
|-----|-----------|
| One simple breakthrough trial stub OK | Full family catalog + unique rare set |
| Same code path for player and any NPC who breakthroughs | Off-screen NPC tribulations write history |
| Template narrative | Rich instance scripts + AI description after resolve |

---

## Tradeoff summary

1. **Shared tribulation engine** over player-only drama → world simulation integrity.  
2. **Typed families** over one generic “roll d20” → signature identity.  
3. **Instance records** over pure narration → persistence and Heaven's Will hooks.

---

## Out of scope / non-goals

- Writing dozens of named lightning sets here.
- Grotesque gore set pieces.
- AI deciding pass/fail.

---

## Unresolved design questions

1. Can cultivators postpone a queued heavenly tribulation? At what cost?
2. Are heart demons skippable with treasures, or only mitigated?
3. Frequency of unique tribulations for ordinary vs Boundless Foundation paths?
4. Do profession shortcuts (pills) reduce severity without changing ruleset (item effects—not unique rules)?
5. Spectator rules (sects watching a heavenly tribulation)?

---

## Expansion notes

- Heaven's Will can raise severity or force heavenly/heart-demon weight ([HEAVENS_WILL.md](HEAVENS_WILL.md)).
- Related: [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [REALMS.md](REALMS.md), [TECHNIQUES.md](TECHNIQUES.md), [GAME_VISION.md](GAME_VISION.md).
