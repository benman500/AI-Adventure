# Development Roadmap

## Purpose

Orders delivery so the project stays a **world simulation** with small MVP increments and **large architecture** from day one. Stack is not locked.

## Confirmed design

- Engine simulates the world and owns statistics, inventory, money, cultivation, breakthroughs, combat, time, permanent facts, and committed techniques.
- AI narrates; AI never decides numbers or writes saves.
- MVP stays intentionally small; architecture anticipates the complete vision ([MVP_SCOPE.md](MVP_SCOPE.md), [GAME_VISION.md](GAME_VISION.md)).
- Technique encyclopedia scalability, Boundless Foundation Path, multi-axis cultivation, tribulations, and Heaven's Will are first-class architectural concerns early—not afterthoughts.
- Players and NPCs share one cultivation ruleset; CPI stays internal-only.
- Repository layout: `docs/`, `src/`, `tests/`, `saves/`, `assets/`, `prompts/`.

## Proposed details

### Phase 0 — Design approval

- Approve living docs under `docs/` (including [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md), [TRIBULATIONS.md](TRIBULATIONS.md), [HEAVENS_WILL.md](HEAVENS_WILL.md)).
- Resolve only questions required to start Phase 1.
- No gameplay code required to finish this phase.

### Phase 1 — Simulation engine core + scalable schemas

**MVP implementation**

- Character/NPC shared cultivation schema: locked early realms, stages, path type, Body/Qi/Soul/Dao/Foundation Quality, money/inventory, time.
- Persistence under `saves/`; engine-owned writes only.
- Tests for core state transitions (including breakthrough outcome enums).

**Long-term architecture in the same phase**

- Technique record schema (rich metadata fields allowed to be sparse).
- Tribulation template/instance stubs; Heaven's Will attention stub.
- World/time concept and extension points for factions, history, and instances—even if mostly empty.
- Clear module boundaries so living sects, economies, and immortal bands can attach later.
- No UI surface for numerical combat power.

### Phase 2 — MVP playable loop

- Per [MVP_SCOPE.md](MVP_SCOPE.md): creation, tiny cultivation loop, profession earn, small technique set on real schema, save/load, stub narration.
- Prove Boundless Foundation costs/behavior differ from ordinary path.
- Presentation text-first; stack unresolved.

### Phase 3 — Early depth

- Deeper breakthrough/tribulation rules once decided; richer profession actions.
- Grow technique count carefully without abandoning schema.
- Background packages with skills/reputation—still not classes.
- Thin vertical slices of faction or economy only if explicitly useful; do not fake “done” living worlds.

### Phase 4 — AI narration + proposal pipelines

- AI narration behind [AI_BOUNDARIES.md](AI_BOUNDARIES.md).
- Optional AI-assisted technique (and similar) **draft → engine commit → permanent object** pipeline.
- Graceful offline degradation for play loop.

### Phase 5 — Modular living-world systems

- Living sects, kingdoms, tournaments, secret realms, inheritances, economies (auctions, caravans, trade routes), relationships/NPC memories, procedural locations, immortal ascension—as modular systems.
- Preserve long-term consistency over spectacle ([GAME_PRINCIPLES.md](GAME_PRINCIPLES.md)).

```mermaid
flowchart LR
  p0[Phase0_Design]
  p1[Phase1_EngineAndSchemas]
  p2[Phase2_MVPLoop]
  p3[Phase3_EarlyDepth]
  p4[Phase4_AIAndProposals]
  p5[Phase5_LivingWorld]
  p0 --> p1 --> p2 --> p3 --> p4 --> p5
```

### Folder alignment

| Folder | Role |
|--------|------|
| `docs/` | Living design |
| `src/` | Simulation engine + presentation |
| `tests/` | Engine truth tests |
| `saves/` | Persistence |
| `assets/` | Static media |
| `prompts/` | AI style from Phase 4 |

### Technology stance

- Locked in [TECH_STACK.md](TECH_STACK.md): Python 3.14+, FastAPI, SQLite, SQLAlchemy 2, Alembic, Pydantic, pydantic-settings, Jinja2 + HTML/CSS/vanilla JS, pytest; AI via abstract Narrator (optional at runtime).
- No Django/Flask/React/Vue/Angular/Node; no Docker during MVP.

## Out of scope / non-goals

- Cloud multiplayer commitment in this pass.
- Building AI before engine authority exists.
- Filling thousands of techniques before schemas and MVP loop are real.

## Unresolved design questions

- Packaging for early testers?
- Which open design questions block Phase 1 coding?
- CI and test depth policy?
- Min Python 3.14.x / async vs sync SQLAlchemy for MVP ([TECH_STACK.md](TECH_STACK.md))?


## Expansion notes

- Phase gate: do not treat Phase 5 content as Phase 2 scope.
- Prefer data-driven techniques, backgrounds, sites, and factions.
- Related documents: [MVP_SCOPE.md](MVP_SCOPE.md), [WORLD_MODEL.md](WORLD_MODEL.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md).
