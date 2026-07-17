# Development Roadmap

## Purpose

Orders delivery so the project stays a **world simulation** with small MVP increments and **large architecture** from day one.

This document distinguishes two numbering systems:

| Kind | Meaning |
|------|---------|
| **Gameplay system phases** | Incremental feature delivery after the opening slice (Cultivation 1–3, Event 4, Location 5, …). **This is the active implementation roadmap.** |
| **Historical delivery milestones** | Earlier project gates (design approval, scaffold, MVP loop). Kept below for archaeology. |

Stack is locked in [TECH_STACK.md](TECH_STACK.md).

---

## Confirmed design

- Engine simulates the world and owns statistics, inventory, money, cultivation, breakthroughs, combat, time, permanent facts, and committed techniques.
- AI narrates; AI never decides numbers or writes saves.
- MVP stays intentionally small; architecture anticipates the complete vision ([MVP_SCOPE.md](MVP_SCOPE.md), [GAME_VISION.md](GAME_VISION.md)).
- Technique encyclopedia scalability, Boundless Foundation Path, multi-axis cultivation, tribulations, and Heaven's Will are first-class architectural concerns early—not afterthoughts.
- Players and NPCs share one cultivation ruleset; CPI stays internal-only.
- Repository layout: `docs/`, `src/`, `tests/`, `saves/`, `assets/`, `prompts/`.
- World content uses **modular regional packs** ([LOCATIONS.md](LOCATIONS.md)).

---

## Active roadmap — gameplay system phases

### Completed

| Phase | System | Status |
|------:|--------|--------|
| 1 | Cultivation framework (realms, meters) | Shipped |
| 2 | Active cultivation sessions | Shipped |
| 3 | Breakthrough engine | Shipped |
| 4a | Event engine core | Shipped (`0007_event_engine`) |
| 4b | Live cultivation session event hook | Shipped |
| 4c | Event tooling, validation, expanded catalog | Shipped |
| **5a** | **Location catalog, packs, presence** | **Shipped (`0008_locations`)** |
| **5b** | **Travel graph + LocationService + WorldClock + live after_story_travel** | **Shipped** |
| **5c** | **Location actions (explore / inspect) + UI** | **Shipped** |
| **6a** | **Modifier Framework design lock** | **Docs locked** — [MODIFIER_FRAMEWORK.md](MODIFIER_FRAMEWORK.md) |
| **6b** | **Modifier Framework engine stub** | **Shipped** — `engine/modifiers.py` + type/bundle catalogs + unit tests; no gameplay change |
| **6c** | **Techniques (first modifier source)** | **Shipped** — catalog + mastery (`0009`) + starters; sessions + breakthroughs consume `ModifierSnapshot` |
| **6d** | **Event Selection Bias consumer** | **Shipped** — generic `weight_mult` / `chance_flat` + category; Event Engine soft bias only |
| **7** | **Spiritual Roots** | **Shipped** — second modifier source; see [SPIRITUAL_ROOTS.md](SPIRITUAL_ROOTS.md) |

### In progress / next

| Phase | System | Scope |
|------:|--------|--------|
| 9c | NPC interaction expansion | inspect / ask_guidance / event hooks |
| 9d | Sect membership & standing | Join eligibility, rank, local standing |
| 10 | Combat expansion | Beyond stubs; bounded combat modifiers reuse the framework |
| 11 | World simulation | Off-screen ticks, broader living world |
| 12 | AI-generated story arcs | Narration/proposals only; engine commits |

**Deferred by decision:** Profession earn loop until after Locations, Techniques, and Spiritual Roots.

**Travel hook:** Shipped in Location Phase **5b**.

**Canonical Phase 6–9 order:** 6a → 6b → 6c → 6d → **7 Roots** → **8 Alchemy** → **9a–9b NPC vertical slice**. Stop after 9b before expanding interactions (9c).

```mermaid
flowchart LR
  c1[Cultivation_1to3]
  e4[Event_4abc]
  l5a[Location_5a]
  l5b[Travel_5b]
  l5c[Explore_5c]
  m6a[Modifier_6a]
  m6b[Modifier_6b]
  t6c[Techniques_6c]
  e6d[EventBias_6d]
  r7[Roots_7]
  a8[Alchemy_8]
  n9[NPC_9ab]
  c1 --> e4 --> l5a --> l5b --> l5c --> m6a --> m6b --> t6c --> e6d --> r7 --> a8 --> n9
```

---

## Historical delivery milestones (archive)

These phases describe how the project was bootstrapped. Do not use them as the forward plan.

### Milestone / Phase 0 — Design approval

- Living docs under `docs/` approved.
- No gameplay code required to finish.

### Milestone / Phase 1 (historical) — Simulation engine core + schemas

- Shared cultivation schema seeds, persistence under `saves/`, Alembic ownership.
- Extension points for techniques, tribulations, Heaven's Will.

### Milestone / Phase 2 (historical) — MVP playable loop

- Character creation, opening story, first cultivation loop, path choice ([OPENING_STORY.md](OPENING_STORY.md)).
- Profession earn and technique records were MVP goals; profession is now deferred; techniques are gameplay Phase **6c** (after Modifier Framework 6a–6b).

### Milestone / Phase 3 (historical) — Early depth

- Deeper breakthrough/tribulation; background packages — partially superseded by cultivation system Phases 1–3.

### Milestone / Phase 4 (historical) — AI narration

- Still future work; renumbered as gameplay Phase 12 for story arcs / narration pipelines. Event engine took the “Phase 4” label in the cultivation/event overhaul.

### Milestone / Phase 5 (historical) — Modular living-world systems

- Long-term bucket (sects, economies, procedural locations). Location substrate started early as gameplay Phase 5a–5c; full living-world remains Phases 9–11.

### Folder alignment

| Folder | Role |
|--------|------|
| `docs/` | Living design |
| `src/` | Simulation engine + presentation |
| `tests/` | Engine truth tests |
| `saves/` | Persistence |
| `assets/` | Static media |
| `prompts/` | AI style (when narration ships) |

### Technology stance

- Locked in [TECH_STACK.md](TECH_STACK.md): Python 3.14+, FastAPI, SQLite, SQLAlchemy 2, Alembic, Pydantic, pydantic-settings, Jinja2 + HTML/CSS/vanilla JS, pytest; AI via abstract Narrator (optional at runtime).
- No Django/Flask/React/Vue/Angular/Node; no Docker during MVP.

## Out of scope / non-goals

- Cloud multiplayer commitment in this pass.
- Building AI before engine authority exists.
- Filling thousands of techniques before schemas and MVP loop are real.
- Profession loop before Locations / Techniques / Spiritual Roots.

## Unresolved design questions

- Packaging for early testers?
- CI and test depth policy?
- Async SQLAlchemy later vs keep sync ([TECH_STACK.md](TECH_STACK.md))?

## Expansion notes

- Prefer data-driven techniques, backgrounds, sites, and factions.
- Mechanical influences from techniques and later sources share [MODIFIER_FRAMEWORK.md](MODIFIER_FRAMEWORK.md).
- Related: [MVP_SCOPE.md](MVP_SCOPE.md), [LOCATIONS.md](LOCATIONS.md), [WORLD_MODEL.md](WORLD_MODEL.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [EVENT_ENGINE.md](EVENT_ENGINE.md), [TECHNIQUES.md](TECHNIQUES.md), [MODIFIER_FRAMEWORK.md](MODIFIER_FRAMEWORK.md), [DECISIONS.md](DECISIONS.md).
