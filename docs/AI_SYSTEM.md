# AI System

## Purpose

Owns how AI is integrated for narration, dialogue, descriptions, and assisted content drafting—without ever owning simulation truth. Boundary contract details also live in [AI_BOUNDARIES.md](AI_BOUNDARIES.md).

## Confirmed design

- Project identity: **world simulation first**; AI is narration/dialogue/description ([GAME_PRINCIPLES.md](GAME_PRINCIPLES.md)).
- AI **never** determines numerical outcomes.
- AI **never** directly modifies saved state.
- Tone: serious xianxia; no parody; no fourth-wall humor; respect content toggles ([GAME_VISION.md](GAME_VISION.md)).
- Techniques (and similar objects) drafted with AI become permanent only via **engine commit**.
- **MVP implementation:** AI not required; stub narration allowed.
- **Long-term architecture:** structured event → narration pipeline and proposal → validate → commit pipeline designed early.

## Proposed details

### Runtime narration pipeline

1. Engine resolves intent and commits state.
2. Engine emits structured event payloads (actors, place ids, deltas already applied).
3. AI renders narration/dialogue/description.
4. UI displays text; player returns intents to the engine.

### Content proposal pipeline

1. Draft technique/location/lore candidate (AI or tools).
2. Engine validates schema, balance gates, world constraints.
3. Engine persists accepted objects.
4. Narration may describe discovery only after commit.

### Prompt assets

- Live under `prompts/` when implemented.
- Style and safety only; no authority to mutate state.

### MVP vs architecture

| MVP implementation | Long-term architecture |
|--------------------|------------------------|
| Templates / stubs | Model-backed narration |
| No proposals required | Technique/worldgen proposal commits |
| Offline play works | Optional online models with offline degrade |

## Out of scope / non-goals

- Choosing a vendor in this document.
- Letting the model call write-save tools.

## Unresolved design questions

- Model hosting, cost, latency?
- Memory: what stays in engine vs ephemeral context windows?
- Logging/replay of AI text?
- Auto-accept tiers for low-power drafts?
- Streaming vs full responses?

## Expansion notes

- Keep [AI_BOUNDARIES.md](AI_BOUNDARIES.md) as the hard prohibitions reference; this doc covers pipelines and product integration.
- Related: [TECHNIQUES.md](TECHNIQUES.md), [NPCS.md](NPCS.md), [WORLD_GENERATION.md](WORLD_GENERATION.md), [DATABASE.md](DATABASE.md), [MVP_SCOPE.md](MVP_SCOPE.md).
