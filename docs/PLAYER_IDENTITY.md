# Player Identity

## Purpose

Defines how **character creation identity** is formed—personality questioning, hidden traits, dialogue tendencies, and Dao affinities—while keeping **background as upbringing, not destiny**. Creation flow basics remain in [CHARACTER_CREATION.md](CHARACTER_CREATION.md); backgrounds in [BACKGROUNDS.md](BACKGROUNDS.md). Boundless path choice is a **story event**, not part of identity ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).

---

## Confirmed design

- Character creation should include **personality questions**.
- Answers influence:
  - **Hidden traits**
  - **Dialogue tendencies**
  - **Possible Dao affinities**
- **Background determines upbringing, not destiny** ([GAME_PRINCIPLES.md](GAME_PRINCIPLES.md), [BACKGROUNDS.md](BACKGROUNDS.md)).
- No reincarnation as default player origin.
- Identity must **not** grant unique cultivation rules or protagonist-only formulas; traits bias choices and affinities under shared systems.
- **Boundless Foundation Path is not chosen at creation** and is **not** an automatic result of personality answers. Personality must **not** auto-pick Boundless; the informed permanent choice arrives only via the mandatory early story event ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).
- Engine stores traits/affinities; AI uses them for dialogue tone—does not invent durable trait changes without engine events.

---

## Proposed details

### Creation pipeline (updated)

1. Identity (name, optional cosmetics—unresolved).  
2. Background (upbringing package).  
3. **Personality questions** (this document).  
4. Apply starting packages + hidden trait/affinity seeds (provisional ordinary cultivation).  
5. Enter world — Boundless choice via story event later, not in this pipeline.

### Personality questions (proposed design rules)

| Rule | Intent |
|------|--------|
| Small set (e.g. 5–10) | Fits creation pacing; avoids quiz burnout |
| Situational moral/practical dilemmas | Serious xianxia tone; no parody / fourth-wall |
| No single “correct” path | Avoid destiny scoring |
| Map to trait tags + Dao affinity weights | Data-driven, extensible |
| Visible summary optional; traits may stay partly hidden | Mystery without spreadsheet dump |

Example **categories** (not final question text): duty vs ambition, mercy vs necessity, tradition vs innovation, coin vs honor, solitude vs fellowship, risk vs patience.

### Hidden traits (proposed)

- Tags such as vindictive, meticulous, soft-hearted, glory-seeking, distrustful—used by dialogue weighting, heart-demon eligibility, sect politics reactions.
- Traits shift slowly through **deeds** (engine events), not by AI whim.
- Same trait schema can exist on NPCs long-term for simulation parity (proposed architectural lean).

### Dialogue tendencies

- Preferred intents order, verbosity, insult thresholds, bargaining style.
- Local reputation still gates what others will entertain ([REPUTATION.md](REPUTATION.md)).

### Dao affinities

- Question answers seed **possible** Dao affinities (weights), not locked Daos.
- Background may add profession-adjacent affinity lean; identity questions may lean sword, healing, commerce-as-path, etc. ([DAO_SYSTEM.md](DAO_SYSTEM.md)).
- Affinities make some profession→Dao ripenings and technique resonances smoother; they never forbid other Daos.

### Background vs identity

| Background | Identity (questions/traits) |
|------------|-----------------------------|
| Skills, contacts, possessions, local reputation seeds | Hidden traits, dialogue lean, Dao affinity weights |
| Upbringing facts | Disposition under pressure |
| Not destiny | Not destiny |

### MVP vs architecture

| MVP | Long-term |
|-----|-----------|
| Short question set + few traits | Rich trait ecology; NPC shared traits |
| Affinity tags only | Full interplay with Dao trials and heart demons |
| Stub dialogue lean | Deep dialogue planning |

---

## Tradeoffs

1. **Hidden traits vs full transparency** — hidden preserves discovery; transparency helps player intent. Propose partial: player picks vibe, exact tags may stay soft-hidden.  
2. **Personality → Boundless auto-pick** — **forbidden**. Boundless is a story-event choice, never scored or assigned from creation answers. Optional warning copy about hard paths may exist later only as flavor, never as an auto-commit.  
3. **Player-only trait system vs shared actor traits** — shared traits scale world sim; player-only is faster for MVP but weaker simulation.

---

## Out of scope / non-goals

- Reincarnation quiz packs.
- Alignment charts / global good-evil from answers ([REPUTATION.md](REPUTATION.md)).
- Unique physique rewards based solely on “right” answers.
- Cultivation path selection during identity/creation ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).

---

## Unresolved design questions

1. Exact question count and authoring tone guide?
2. Which traits are player-visible after creation?
3. Can players retake/reshape personality later via roleplay arcs?
4. Age/gender/appearance customization scope?
5. Do questions differ by selected background, or stay universal?

---

## Expansion notes

- Store `trait_tags[]`, `dialogue_profile_id`, `dao_affinity_weights{}` on the actor record.
- Related: [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [BACKGROUNDS.md](BACKGROUNDS.md), [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md), [DAO_SYSTEM.md](DAO_SYSTEM.md), [REPUTATION.md](REPUTATION.md), [TRIBULATIONS.md](TRIBULATIONS.md), [SECT_LIFE.md](SECT_LIFE.md).
