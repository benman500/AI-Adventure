# Cultivation System

## Purpose

Defines how personal power is cultivated: multi-axis cultivation (Body, Qi, Soul, Foundation Quality), Dao understanding ([DAO_SYSTEM.md](DAO_SYSTEM.md)), major realms/stages, Boundless Foundation Path, breakthroughs, and links to tribulations and techniques. Professions remain separate ([PROFESSIONS.md](PROFESSIONS.md)). Realm catalog detail: [REALMS.md](REALMS.md). Tribulations: [TRIBULATIONS.md](TRIBULATIONS.md). Discovery and choice of Boundless are owned by [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md).

---

## Confirmed design

### Cultivation vs profession

- **Cultivation** determines **personal power**.
- **Profession** earns **resources, reputation, money, influence, and knowledge**.
- Neither replaces the other.

### One ruleset for all cultivators

- **Players and NPCs use exactly the same cultivation systems.**
- The player must **never** receive unique cultivation rules, hidden protagonist formulas, or exclusive breakthrough math.
- Differences come only from **state** (resources, choices, Foundation Quality, techniques known, Heaven's Will pressure, etc.), never from a separate player rules pipe.

### Realms and power scaling

- Cultivation uses **major realms** and **minor stages**.
- Crossing a major realm is an **enormous** power increase; progression is **exponential**, not linear.
- Combat compass: ~**50 competent peak** of realm N ≈ **1 competent early** of realm N+1.
- Boundless Foundation high mastery may **compete with** ordinary early of N+1 under competent conditions.
- Engine-authoritative outcomes; AI never decides numbers.
- **Combat Power Index (CPI)** (if used) is **internal engine-only**. Players must **never** see numerical combat power values—only realm, stage, qualitative cues, injuries, and narration.

### Locked early major realms

These four are **permanent** first-ladder design (not placeholders):

| Order | Realm |
|------:|-------|
| 1 | Body Tempering |
| 2 | Qi Condensation |
| 3 | Foundation Establishment |
| 4 | Core Formation |

Further realms may be added above later; these four are locked ([REALMS.md](REALMS.md)).

### Multi-axis cultivation (separate systems)

Cultivation expands into interacting systems. Each is engine-tracked for **every** cultivator (player and NPC):

| System | Role |
|--------|------|
| **Body** | Physical tempering, durability, bodily strength |
| **Qi** | Accumulated/circulated energy; core of many arts |
| **Soul** | Divine sense / soul force; perception and soul arts |
| **Dao** | **Understanding** of paths/laws—not a combat statistic. Detailed in [DAO_SYSTEM.md](DAO_SYSTEM.md). Influences techniques, breakthroughs, tribulations. |
| **Foundation Quality** | Structural soundness of the cultivator’s base—flawed vs nearly flawless |

Axes progress with practice, resources, techniques, and breakthrough results. They are **not** separate “player-only” meters. **Dao must not be presented or used as raw combat power numbers**; realm/Body/Qi/Soul/Foundation Quality carry power, while Dao carries comprehension.

### Boundless Foundation Path

Mechanical characteristics of the Boundless path (shared by player and NPC). **How players discover and choose** the path—mandatory early story event (~first 30 minutes), informed permanent irreversible choice, not creation—is owned by [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md). Players **start without a path choice at creation** (provisional ordinary cultivation until that event).

The Boundless Foundation Path is a **hard path**—**not objectively superior**. Ordinary cultivation after being **fixed** is a **fully viable** first-class play style with baseline costs and pacing. Boundless demands far greater time, resources, and perseverance for extraordinary long-term potential ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).

Available to **any** cultivator (player or NPC) who walks Boundless—not destiny, not player-exclusive math. Game content must remain completable and rewarding on the ordinary path.

| Characteristic | Effect |
|----------------|--------|
| Breakthroughs | Require far more cultivation |
| Resources | Greatly increased costs |
| Tribulations | Much harder |
| Foundations | Nearly flawless Foundation Quality trajectory |
| Power quality | Stronger qi, body, and future breakthroughs |
| High mastery | May compete with ordinary cultivators one major realm higher |

### Major breakthroughs — outcome space

Major realm breakthroughs (and other designated breakthroughs) must support at least:

| Outcome | Meaning |
|---------|---------|
| **Success** | Advance as intended |
| **Failure** | No advance; durable costs possible |
| **Partial success** | Incomplete advance or deferred completion |
| **Damaged foundations** | Lasting Foundation Quality harm (and related scars) |
| **Unique tribulations** | Instance-specific trials drawn from the tribulation system |

Exact probabilities and tables are designable later; the **outcome vocabulary is confirmed**.

### Tribulations as a signature feature

Tribulations are a **signature pillar** of the game—including heavenly tribulations, heart demons, mental trials, and dao comprehension trials where appropriate. See [TRIBULATIONS.md](TRIBULATIONS.md).

### Heaven's Will

The world includes a balancing system (**Heaven's Will**) that reacts to major events and powerful cultivators. See [HEAVENS_WILL.md](HEAVENS_WILL.md).

### Techniques

Enormous permanent encyclopedia; MVP ships few records on scalable schema. AI drafts commit only via engine ([TECHNIQUES.md](TECHNIQUES.md)).

---

## Proposed details

### How axes relate to realms (proposed)

- **Major realm / stage** remains the primary **band** for the 50:1 compass and presentation.
- Body / Qi / Soul / Dao / Foundation Quality are **component systems** that feed readiness, tribulation type weights, technique gates, and internal CPI—without exposing CPI to players.
- A cultivator can be unbalanced (e.g. strong Body, weak Soul); that creates niches and weaknesses, not a second secret player ruleset.

**Tradeoff — five full parallel realm ladders vs components under one realm spine**

| Approach | Pros | Cons |
|----------|------|------|
| Five independent realm ladders | Maximal sim depth | UI/cognitive overload; breaks one 50:1 story |
| **One realm spine + five component systems (proposed)** | Preserves exponential bands; allows rich buildcraft | Needs clear presentation of components |

**Decision lean:** One locked realm spine; five components.

### Foundation Quality (proposed bands)

Qualitative bands for presentation (exact numeric internals hidden): fragmented / flawed / stable / solid / near-flawless / flawless (names tunable). Boundless Foundation Path biases strongly toward the high end; damaged breakthrough outcomes push downward.

### Ordinary vs Boundless Foundation Path

| Aspect | Ordinary | Boundless Foundation |
|--------|----------|-------------------|
| Axis investment needed | Baseline | Much higher across relevant axes |
| Resources / time | Baseline | Greatly increased |
| Tribulations | Baseline signature set | Harder / rarer unique rolls |
| Foundation Quality | Competent ceiling common | Nearly flawless target |
| High mastery vs N+1 ordinary early | Unlikely | Plausible competition |

### Engine tracking (every actor)

- Realm id + stage
- Path type (ordinary / Boundless Foundation)
- Body, Qi, Soul, Dao, Foundation Quality
- Progress / breakthrough readiness
- Active tribulation instance (if any)
- Technique mastery links
- Heaven's Will attention modifiers (reference)
- Durable scars from failed/partial/damaged outcomes

### Minor stages (proposed)

`early` / `mid` / `late` / `peak` on the locked early realms ([REALMS.md](REALMS.md)).

---

## Out of scope / non-goals

- Player-only cultivation cheats or “heaven’s chosen” math.
- Showing CPI or raw combat power numbers in UI.
- Inventing full post–Core Formation realm lists in this pass.
- Application code.
- Authoring the Boundless discovery/choice story beat (owned by [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).

---

## Unresolved design questions

- Exact presentation of Body/Qi/Soul/Dao/Foundation Quality (meters, ranks, prose-only)?
- Weights of each axis into breakthrough readiness and hidden CPI?
- Axis soft-caps per major realm?
- Which breakthroughs besides major-realm crossings use the full outcome vocabulary?

---

## Expansion notes

- Related: [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md), [REALMS.md](REALMS.md), [TRIBULATIONS.md](TRIBULATIONS.md), [HEAVENS_WILL.md](HEAVENS_WILL.md), [TECHNIQUES.md](TECHNIQUES.md), [DAO_SYSTEM.md](DAO_SYSTEM.md), [NPCS.md](NPCS.md), [COMBAT.md](COMBAT.md), [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md).
