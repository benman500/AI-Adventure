# Design Review

## Purpose

Post-design audit of the documentation set after the final pre-implementation pass (including Dao, sect life, reputation, and player identity). Records **contradictions**, **duplicate systems**, and **missing architecture**. No application code.

Review date context: final design pass before implementation.

---

## Document inventory

| Doc | Owns |
|-----|------|
| GAME_VISION / GAME_PRINCIPLES | Pitch, tone, permanent principles |
| CULTIVATION_SYSTEM / REALMS / TRIBULATIONS / HEAVENS_WILL / DAO_SYSTEM / BOUNDLESS_FOUNDATION | Power, realms, trials, world pressure, understanding, Boundless discovery/choice |
| TECHNIQUES / PROFESSIONS / ECONOMY | Arts, work, markets |
| BACKGROUNDS / CHARACTER_CREATION / PLAYER_IDENTITY | Origin and identity |
| SECTS / SECT_LIFE / REPUTATION / NPCS | Society and opinion |
| WORLD_MODEL / WORLD_GENERATION | Entity vocabulary and content genesis |
| COMBAT / AI_SYSTEM / AI_BOUNDARIES / DATABASE | Conflict, AI contract, persistence |
| MVP_SCOPE / DEVELOPMENT_ROADMAP | Delivery gates |
| CHARACTER_CREATION, WORLD_MODEL, AI_BOUNDARIES | Legacy helpers still valid alongside newer splits |

---

## Contradictions found (and resolution status)

### 1. Dao as cultivation “axis” vs Dao as understanding (was contradictory)

- **Tension:** [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md) listed Dao beside Body/Qi/Soul in a power-like axis table; new [DAO_SYSTEM.md](DAO_SYSTEM.md) states Dao is understanding, not statistics.
- **Resolution applied:** Cultivation doc now states Dao is comprehension substrate owned by DAO_SYSTEM; not raw combat power / not shown as combat numbers.
- **Residual risk:** Writers may still say “raise Dao” like a stat—keep presentation rules tight in UI design later.

### 2. Reputation language sounded global

- **Tension:** Backgrounds/creation/profession docs said “reputation” without local scope; new [REPUTATION.md](REPUTATION.md) forbids global good/evil meters.
- **Resolution applied:** Character creation and professions pointed at local opinion / REPUTATION.md.
- **Residual risk:** [ECONOMY.md](ECONOMY.md) still speaks generically—should explicitly consume local settlement/faction opinion (architecture gap below).

### 3. Sect docs overlap without conflict

- [SECTS.md](SECTS.md) = faction entity; [SECT_LIFE.md](SECT_LIFE.md) = living loop. **Not a contradiction** if SECTS remains the container and SECT_LIFE the daily sim. Cross-link added.

### 4. Influence vs reputation

- Profession earns **influence**; reputation is local opinion. **Mild ambiguity:** influence might be read as a global currency.
- **Recommended clarification (open):** treat influence as **spendable political capital with a specific faction/office**, always scoped—never a global bar. Not fully rewritten across ECONOMY yet.

### 5. CPI / “combat power” visibility

- Confirmed hidden across COMBAT/REALMS/CULTIVATION. **No remaining contradiction** if all UIs obey it.

### 6. Player uniqueness

- Confirmed shared rulesets. PLAYER_IDENTITY hidden traits are **biases**, not unique cultivation math—**aligned** if implementation refrains from protagonist formulas.

---

## Duplicate systems (consolidation map)

| Topic | Primary owner | Secondary / avoid duplicating rules in |
|-------|---------------|----------------------------------------|
| Realm ladder & stages | REALMS | CULTIVATION_SYSTEM (summary only) |
| Boundless Foundation | BOUNDLESS_FOUNDATION (discovery/choice story); CULTIVATION_SYSTEM (mechanics) | CHARACTER_CREATION must not own path choice—story event, not creation |
| Tribulations | TRIBULATIONS | CULTIVATION (outcome vocabulary), HEAVENS_WILL (modifiers) |
| Dao understanding | DAO_SYSTEM | CULTIVATION (axis pointer), TECHNIQUES (affinity), PLAYER_IDENTITY (seeds) |
| Profession ranks/jobs | PROFESSIONS | ECONOMY (prices), DAO_SYSTEM (ripening) |
| Sect faction entity | SECTS | SECT_LIFE (daily life), REPUTATION (opinions) |
| Local opinions | REPUTATION | BACKGROUNDS (seeds), SECT_LIFE/ECONOMY (consumers) |
| AI authority | AI_BOUNDARIES | AI_SYSTEM (pipelines) |
| World entity kinds | WORLD_MODEL | WORLD_GENERATION (how entities appear) |
| Creation flow | CHARACTER_CREATION | PLAYER_IDENTITY (questions/traits), BACKGROUNDS (packages) |

**AI_BOUNDARIES vs AI_SYSTEM:** intentional split (contract vs pipelines)—keep both; do not fork a third AI doc.

**WORLD_MODEL vs WORLD_GENERATION:** intentional split—keep both.

---

## Missing architecture (gaps before coding)

### High priority (should lock or stub schemas in Phase 1)

1. **Unified actor schema** — One `Actor` record used for player and NPCs: cultivation, axes, Dao paths, traits, professions, technique mastery, Heaven's Will attention refs.
2. **Opinion graph storage** — REPUTATION edges with facets; default-neutral sparse model ([REPUTATION.md](REPUTATION.md)).
3. **Sect schedule/tick service** — SECT_LIFE requires an off-screen tick even when player absent ([SECT_LIFE.md](SECT_LIFE.md)).
4. **Dao path catalog + profession ripening table** — every profession_id maps to at least one ripenable `dao_path_id` ([DAO_SYSTEM.md](DAO_SYSTEM.md)).
5. **Breakthrough outcome + tribulation instance pipeline** — enums already confirmed; wiring still design-light on probabilities.
6. **Economy ↔ local reputation** — price modifiers must key off settlement/faction opinions explicitly in ECONOMY (doc lag).
7. **Presentation layer rules** — centralize “never show CPI / global karma / Dao scoreboard” for UI (could be a short UX appendix later).

### Medium priority

8. **Simulation tiers for NPCs/sect cohorts** — mentioned in SECT_LIFE/NPCS; needs a single policy doc section or SIMULATION_TIERS note.
9. **Rumor vs opinion** — REPUTATION distinguishes them; no rumor entity design yet.
10. **Time model** — session fantasy (15–60 min) vs world clock vs sect schedule vs commission jobs; still fragmented across docs.
11. **Identity trait schema on NPCs** — PLAYER_IDENTITY proposes shared traits long-term; NPCS does not yet require trait fields.
12. **Content pack vs per-save invented techniques/Daos** — DATABASE open question still blocks AI commit strategy.

### Lower priority (post-MVP architecture still noted)

13. Kingdom vs sect authority matrix.  
14. Immortal-band naming beyond Core Formation.  
15. Full tournament module doc (only referenced).  
16. Romance systems beyond tone toggles.  
17. Disguise/false identity vs reputation graph.

---

## Consistency checklist (confirmed pillars)

| Pillar | Status across docs |
|--------|-------------------|
| World sim, not pure AI adventure | Consistent |
| Engine authority; AI narrates | Consistent |
| Persistent important state | Consistent |
| Background ≠ class/destiny | Consistent; PLAYER_IDENTITY reinforces |
| Profession ≠ cultivation power | Consistent; Dao ripening clarified |
| Boundless Foundation choice (story event, not creation), shared rules | Consistent |
| Locked early four realms | Consistent |
| Multi-axis + Dao understanding | Aligned after CULTIVATION fix |
| Tribulations signature | Consistent |
| Heaven's Will ≠ morality meter | Consistent with REPUTATION |
| Local reputation; no global good/evil | New primary; consumers partially updated |
| Living sects without player | SECT_LIFE + principles aligned |
| CPI hidden | Consistent |
| MVP small / architecture large | Consistent |

---

## Recommended doc touch-ups before Phase 1 coding (optional, no code)

1. Patch [ECONOMY.md](ECONOMY.md) to require local reputation price hooks.  
2. Patch [NPCS.md](NPCS.md) to include optional trait + Dao path fields.  
3. Add profession→Dao ripening note table stub under PROFESSIONS or DAO_SYSTEM content pack.  
4. Add a short **TIME_MODEL.md** or section under WORLD_MODEL unifying clocks.  
5. Keep CHARACTER_CREATION / PLAYER_IDENTITY / BACKGROUNDS as the only creation stack—avoid a fourth creation doc.

---

## Verdict

The documentation set is **coherent enough to freeze for implementation planning**, with the Dao understanding clarification applied and new social/identity systems specified. Remaining issues are mostly **missing wiring docs** (time model, economy↔reputation, simulation tiers) rather than unresolved clashes in pillars.

**Do not start application code** until you explicitly approve this review and any follow-up touch-ups you want completed first.
