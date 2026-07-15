# Dao System

## Purpose

Defines **Dao** as comprehension of paths and laws—distinct from cultivation power. Owns how Dao differs from Body/Qi/Soul/realm progression, how professions can ripen into Daos, and how Dao influences techniques, breakthroughs, and tribulations.

Related: [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [PROFESSIONS.md](PROFESSIONS.md), [TECHNIQUES.md](TECHNIQUES.md), [TRIBULATIONS.md](TRIBULATIONS.md), [PLAYER_IDENTITY.md](PLAYER_IDENTITY.md).

---

## Confirmed design

### Dao vs cultivation

| Cultivation | Dao |
|-------------|-----|
| Personal **power**—realms, stages, Body, Qi, Soul, Foundation Quality | **Understanding**—how the cultivator perceives and walks a path |
| Exponential combat band (50:1 compass) | Does **not** replace major-realm power |
| Advanced by practice, resources, breakthroughs | Advanced by insight, living practice, trials, devotion to a way |
| Visible largely as realm/stage/quality cues | Experienced as affinities, insights, technique resonance, trial forms |

- **Dao represents understanding rather than statistics.** It must not become a second Combat Power Index or a player-facing number scoreboard.
- Players and NPCs use the **same** Dao systems (no unique player Dao rules).
- Engine decides Dao advances and trial outcomes; AI narrates insight.

### Profession → Dao

- **Every profession should eventually be capable of becoming a Dao** (e.g. a deep Alchemist's path ripening into a Dao of Alchemy / Refinement).
- Profession ranks still earn resources/reputation/money/influence/knowledge; Dao is the **comprehension** that can emerge from (or alongside) that work—not a class lock.
- Becoming a Dao does **not** forbid other professions; time and focus remain scarce.

### Influence (required hooks)

Dao must be able to influence:

- **Techniques** — resonance, learning speed, evolution eligibility, dao affinity gates
- **Breakthroughs** — readiness flavor, partial-success shapes, which insights stabilize Foundation Quality
- **Tribulations** — especially **dao comprehension trials**, and weights on heart-demon / heavenly forms when a Dao is strained or profound ([TRIBULATIONS.md](TRIBULATIONS.md))

### Relationship to the cultivation “Dao” axis

[CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md) lists **Dao** among multi-axis systems. That axis is confirmed as the **comprehension substrate** owned in detail here—not a raw combat stat. Presentation stays qualitative (insights, affinities, trial results), never “Dao: 87.”

---

## Proposed details

### What a Dao is (data)

**Proposal:** A Dao is a **path record** a cultivator walks:

| Field group | Meaning |
|-------------|---------|
| `dao_path_id` | Catalog path (e.g. linked to profession family, elemental law, sword way) |
| Comprehension depth | Ordered qualitative bands (glimpse → bearing → embodiment → …)—**not** shown as CPI |
| Affinities | Tags that techniques and trials read |
| Tensions | Conflicts between paths (sword vs mercy, profit vs purity)—fuel heart demons |
| Origin | Profession-ripened, technique-led, tribulation-born, identity-seeded ([PLAYER_IDENTITY.md](PLAYER_IDENTITY.md)) |

Actors may hold **multiple** Dao paths at shallow depth; deep embodiment is rare and costly (proposed).

### Profession ripening (proposed)

```mermaid
flowchart LR
  profession[ProfessionPractice]
  understanding[AccumulatedUnderstanding]
  daoPath[DaoPathAwakened]
  trials[DaoComprehensionTrials]
  profession --> understanding
  understanding -->|"threshold + insight event"| daoPath
  daoPath --> trials
  trials -->|"deepens or cracks"| daoPath
```

| Stage | Profession | Dao |
|-------|------------|-----|
| Early | Jobs/recipes only | Optional latent affinity tags |
| Mid | High rank + consistent practice | Path can **awaken** as a Dao |
| Late | Mastery | Dao embodiment enables unique technique evolutions / trial forms |

Alchemy, smithing, medicine, commerce, scholarship, hunting, farming, streetcraft, beastkeeping, administration—and any future profession—should have a **defined ripening route** into a corresponding Dao catalog entry (architecture requirement even if content is sparse in MVP).

### Influence details (proposed)

| System | Dao effect examples |
|--------|---------------------|
| Techniques | Affinity match reduces learning friction; mismatch risks deviation; evolution paths require Dao depth |
| Breakthroughs | Matching Dao stabilizes partial success; opposing Dao tension raises damaged-foundation risk |
| Tribulations | Dao trials test understanding; failed Dao alignment worsens heart demons; heavenly pressure may target high embodiment |

### Presentation rules

| Allowed | Forbidden |
|---------|-----------|
| “Your understanding of flame refinement has deepened” | “Dao stat +3” |
| Trial and insight narration | Global Dao power level HUD numbers |
| Technique resonance cues | Dao as substitute for realm |

### MVP vs architecture

| MVP | Long-term |
|-----|-----------|
| Latent affinity tags from identity/background | Full profession→Dao ripening for every profession |
| Stub dao trial on breakthrough optional | Rich Dao catalog and tensions |
| No need for deep embodiment | Multiple paths, immortal Daos |

---

## Tradeoffs

1. **Understanding bands vs numeric Dao stats** — bands preserve fiction; stats would duplicate CPI sins.  
2. **Profession-linked Daos vs free-only mystical Daos** — linking every profession fulfills the confirmed route; pure mystical Daos can still exist as additional catalog paths.  
3. **One primary Dao vs many** — many shallow + few deep (proposed) honors polymath careers without trivial omni-Dao.

---

## Out of scope / non-goals

- Listing every named Dao in the cosmoverse here.
- Making Dao replace cultivation realms.
- Player-only enlightenment cheats.

---

## Unresolved design questions

1. Qualitative band names and count for comprehension depth?
2. Can a cultivator abandon or shatter a Dao deliberately?
3. Do Boundless Foundation walkers face harder Dao trials by default?
4. How visible are Dao tensions to the player before a heart demon fires?
5. Shared world Dao catalog vs rare unique path inventable via AI commit?

---

## Expansion notes

- Keep Dao path catalog data-driven like techniques.
- Related: [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [PROFESSIONS.md](PROFESSIONS.md), [TECHNIQUES.md](TECHNIQUES.md), [TRIBULATIONS.md](TRIBULATIONS.md), [PLAYER_IDENTITY.md](PLAYER_IDENTITY.md), [HEAVENS_WILL.md](HEAVENS_WILL.md).
