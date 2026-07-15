# Opening Story (Milestone 3)

## Purpose

Documents the **authored Milestone 3 opening slice**: background-specific intros, shared sect pipeline, first cultivation loop, mandatory anomaly, and permanent path choice. This is **MVP implementation content**, not the long-term procedural story or AI narration systems.

## Confirmed design (Milestone 3)

### Scope

| In scope | Out of scope (deferred) |
|----------|-------------------------|
| Three background opening scenes | Full open world |
| Shared leave-home → sect → recruitment pipeline | Freeform AI narration |
| One sect (Verdant Gate) | Combat, tournaments |
| Authored recruitment + first lesson | Complete sect life sim |
| Cultivation methods + breakthrough attempt | NPC schedules, dynamic economies |
| Anomaly + investigation + Elder Yun revelation | Large technique libraries |
| Permanent ordinary vs Boundless choice | Full tribulations |

### Story engine

- **Data-driven** nodes in `src/ai_adventure/data/story/`.
- Each node: stable `id`, `title`, `narrative`, `actions`, `requirements`, `effects`, `next_node`.
- **Authoritative state:** `story_progress.current_node_id` on the save — never inferred from displayed text or chat history.
- Engine module: `engine/story.py`. Routes call `GameAppService`; routes do not embed story rules.

### Anomaly (revised Milestone 3 behavior)

The anomaly is **not** triggered by a fixed practice-session count.

Flow:

1. Player learns cultivation (first lesson).
2. Player uses cultivation methods (**Absorb Qi**, **Stabilize Foundation**, **Calm the Mind**) to build qi and progress.
3. When **qi reserve** and **cultivation progress** reach deterministic thresholds, breakthrough readiness is shown.
4. Player chooses **Attempt Breakthrough** — their first genuine breakthrough attempt.
5. Breakthrough does not occur → anomaly → investigation → mystery framing → Elder Yun Mei.

Presentation: the player is **not** talentless or broken. Instructors are confused; examinations fail to explain the stall; the player becomes a **mystery** until Elder Yun Mei intervenes.

### Boundless historical framing

Elder Yun Mei explains that the Boundless Foundation Path:

- Is **ancient** and once taught openly
- Was **abandoned** due to enormous resource cost and extreme difficulty
- Was completed by very few cultivators
- Survives only in **incomplete manuscripts**
- Is considered by most modern cultivators a **failed or obsolete theory**

Choosing Boundless is a **gamble on an abandoned path**, not a hidden overpowered class.

### Cultivation methods (Milestone 3)

| Method id | Label | Role |
|-----------|-------|------|
| `absorb_qi` | Absorb Qi | Default qi/progress gains |
| `stabilize_foundation` | Stabilize Foundation | Slightly more progress |
| `calm_mind` | Calm the Mind | Slightly more qi |

Mechanics are nearly identical in M3; the interface establishes architecture for future cultivation decisions.

### Content canon

| Entity | Id / name |
|--------|-----------|
| Sect | `sect_verdant_gate` — Verdant Gate Sect, Jade Ridge |
| Passing cultivator | Disciple Lu Han (`npc_passing_cultivator_001`) |
| Examiner | Elder Examiner Feng |
| Instructor | Instructor Pei |
| Revealer | Elder Yun Mei — Foundation Hall, ancient manuscripts |

### Story spine (node ids)

```text
{background}_opening_01 → _02 → _03
  → shared_leave_home_01 → shared_travel_01 → shared_cultivator_01
  → shared_travel_02 → shared_sect_gate_01 → shared_recruitment_01..03
  → shared_lesson_01 → shared_cultivation_01
  → (methods until ready) → attempt_breakthrough
  → shared_anomaly_01 → shared_investigation_01..03 → shared_mystery_01
  → shared_revelation_01 → shared_choice_01
  → shared_post_ordinary_01..02  OR  shared_post_boundless_01..02
```

### Save bootstrap

Milestone 2 saves without `story_progress` receive an entry node on first `/play/{save_id}` load, based on `background_id`.

## Related

- [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [DATABASE.md](DATABASE.md), [ARCHITECTURE.md](ARCHITECTURE.md), [DECISIONS.md](DECISIONS.md)
