# MVP Scope

## Purpose

Defines a **deliberately small** first playable version **and** the **long-term architecture** that must be respected from day one. MVP cuts content; it must not erase or downplay the complete vision.

See also: [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md), [GAME_VISION.md](GAME_VISION.md), [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md).

## Confirmed design

### Dual mandate

| Layer | Mandate |
|-------|---------|
| **MVP implementation** | Intentionally small first playable version |
| **Long-term architecture** | Designed from day one to support the complete vision |

- Do **not** remove or downplay long-term systems in design merely because they are out of MVP.
- Clearly label every major feature as **MVP implementation** vs **long-term architecture**.
- Engine authority, world persistence, and AI boundaries apply in both layers.
- **Creation is backgrounds + identity, not path.** The Boundless Foundation Path is introduced by a **mandatory story event in the first ~30 minutes**—part of the MVP story spine—available regardless of background ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).
- Backgrounds remain non-class upbringing packages (not reincarnation).
- Technique encyclopedia is a **core long-term feature**; MVP ships a **tiny** technique set on **scalable** data structures.
- Early major realms are **locked**: Body Tempering, Qi Condensation, Foundation Establishment, Core Formation.
- Cultivation schema includes **Body, Qi, Soul, Dao, Foundation Quality** for every cultivator.
- **No unique player cultivation rules**; NPCs share the same systems (even if sparsely simulated in MVP).
- Breakthrough outcome vocabulary includes success, failure, partial success, damaged foundations, unique tribulations.
- **CPI / combat power numbers are never shown** to the player.
- Tribulations and Heaven's Will are architectural signature systems (thin stubs allowed in MVP).

## Proposed details

### Goals of the MVP (implementation)

Prove that a player can:

1. Create a character from upbringing background + identity (personality seeds)—**not** path selection.
2. Reach the Boundless Foundation story event within ~30 minutes and make an informed permanent choice: **get fixed (ordinary, fully viable)** or **Boundless (hard path)**.
3. Persist and reload important character (and seed world) state including multi-axis cultivation fields and path type after the event.
4. Advance cultivation through a tiny practice → resource → breakthrough loop with at least a stub tribulation/outcome path; mechanical divergence after Boundless choice.
5. Use a minimal profession action to earn supporting resources / money / reputation / knowledge.
6. Interact with at least a **handful** of techniques stored as first-class persistent records (not hard-coded one-offs).
7. Trust that numbers come from the engine, with stub or template text only (AI optional later)—and never see raw combat power scores.

### MVP implementation — in scope

| Area | MVP inclusion |
|------|----------------|
| Character creation | Backgrounds + identity answers + name — **not** path. Milestone 2 ships three data-driven backgrounds (Merchant Family, Alchemist's Apprentice, Hunter); full ten remain the MVP content goal |
| Boundless story event | Mandatory informed permanent choice in first ~30 min; every background reaches it |
| Cultivation | Tiny loop on locked early realms; axes present; breakthrough outcomes stubbed; ordinary vs Boundless diverge after choice. **Milestone 3** ships opening loop only ([OPENING_STORY.md](OPENING_STORY.md)). |
| Tribulations / Heaven's Will | Minimal stub hooks (same APIs later expanded) |
| Profession | Minimal earn action yielding resources, money, and/or reputation/knowledge — **deferred past Milestone 3** |
| Techniques | Small starter set; full metadata schema present even if many fields are empty — **deferred past Milestone 3** |
| Persistence | Save/load of important state via engine |
| World | Tiny starting context; world clock exists (even if few off-screen actors) |
| Narration | Template/stub text; no AI dependency |
| Authority | Engine resolves all mechanical outcomes |

### MVP implementation — out of scope (content depth)

- Full living sect sims, kingdoms, immortal playable destinations
- Tournaments, auctions, caravans, trade-route networks as full systems
- Thousands of techniques
- Dense dynamic economies
- Deep NPC memory webs / procedural continents
- AI narration as a hard dependency
- Multiplayer

### Long-term architecture — required from day one (design constraints)

Architecture, module boundaries, and data models should anticipate (without implementing fully in MVP):

| System | Architectural expectation |
|--------|---------------------------|
| Technique encyclopedia | Scalable store for thousands of techniques across categories; rich metadata; AI-proposed techniques become permanent world objects after engine commit |
| Living world | World advances without the player; time and permanent facts engine-owned |
| Sects / factions / kingdoms | Entity ids, relations, and goal hooks—not player-only stage dressing |
| Economies | Money/items as data; room for auctions, caravans, trade routes later |
| Social layer | Relationships, reputation, NPC goals/memories as extensible records |
| Vertical cosmology | Lower worlds → secret realms → immortal realms / ascension |
| History | World history and object provenance (techniques, inheritances) as durable data |
| Instances | Tournaments, secret realms, ancient inheritances as modular instance patterns |
| Professions | Parallel to cultivation; earn resources, reputation, money, influence, knowledge |
| Tribulations | Shared instance system; signature families |
| Heaven's Will | Attention/pressure reactions to major events and powerful cultivators |
| Shared actor cultivation | Identical schema/rules for player and NPCs |
| AI layer | Narration only; proposals for new content must pass through engine persistence rules |

### Acceptance criteria (proposed checklist)

**MVP implementation**

- [ ] New game → create character → upbringing background + identity package applied (no path at creation)
- [ ] Every background reaches the Boundless Foundation choice event in the first ~30 minutes — **Milestone 3 opening slice**
- [ ] Boundless choice is informed and permanent: fix→ordinary **or** Boundless hard path — **Milestone 3**
- [ ] Choosing fix clears the anomaly and supports a **viable ordinary** cultivation loop — **Milestone 3**
- [ ] Ordinary vs Boundless show mechanical divergence (cost/tribulation/progress) after the choice — **Milestone 3 partial**
- [ ] Profession-adjacent earn action works — *later milestone*
- [ ] At least a few techniques exist as persistent records with the shared schema — *later milestone*
- [ ] Save/load restores important fields (including path type after the event) — **Milestone 3**
- [ ] Playable with no AI configured — **Milestone 3**
- [ ] No path for AI to write saves directly

**Long-term architecture checks (even in MVP)**

- [ ] Technique records are data-driven and not a closed enum of three hard-coded moves
- [ ] World/time model exists as a first-class concept (however minimal)
- [ ] Documented extension points for factions, instances, and economies remain non-contradictory

### Definition of done

MVP is successful if the loop is honest and persistent **and** the scaffolding does not paint the project into a corner against [GAME_VISION.md](GAME_VISION.md) long-term goals.

## Out of scope / non-goals (document-level)

- Implementing application code in this documentation pass.
- Filling the technique encyclopedia or world gazetteer during MVP.

## Unresolved design questions

- Does MVP include **any combat** at all?
- Exact UI: CLI (proposed default), TUI, or local web shell?
- How many major realms are reachable in MVP?
- Full unique starting packages vs shared templates with flavor?
- Breakthrough failure consequences in MVP?
- How many techniques ship in the MVP starter set (proposed: a small handful)?

## Expansion notes

- Related documents: [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md), [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [WORLD_MODEL.md](WORLD_MODEL.md), [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md).
