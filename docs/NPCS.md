# NPCs

## Purpose

Owns non-player characters as persistent simulation agents with goals, memories, and relationships—not disposable dialogue props.

## Confirmed design

- **Every NPC has goals** (engine-owned) ([GAME_PRINCIPLES.md](GAME_PRINCIPLES.md)).
- The world continues **without the player**; NPCs act on schedules/goals.
- **NPC memories**, **relationships**, and **world history** are long-term architecture goals ([GAME_VISION.md](GAME_VISION.md)).
- AI may voice NPCs from engine-known facts; AI does not invent durable memories into saves without engine commit.
- Tone: serious xianxia—rivalry, betrayal, ambition, occasional non-parodic humor.
- **NPCs and players use exactly the same cultivation systems** (realms, stages, Body/Qi/Soul/Dao/Foundation Quality, Boundless Foundation Path, breakthroughs, tribulations, Heaven's Will). No NPC-only soft math and no player-only cultivation rules.
- Important NPCs may attempt Boundless Foundation Path, suffer damaged foundations, and face unique tribulations under the shared outcome vocabulary.
- **MVP implementation:** few NPCs, thin goal/memory fields; cultivation fields still use the shared schema even if sparsely simulated.
- **Long-term architecture:** scalable NPC records, memory logs, faction membership, off-screen breakthroughs/tribulations, and Heaven's Will attention.

## Proposed details

### NPC record (conceptual)

| Field group | Examples |
|-------------|----------|
| Identity | Name, upbringing flavor, cultivation realm/stage, path type |
| Cultivation axes | Body, Qi, Soul, Dao, Foundation Quality (same as player) |
| Goals | Short- and long-term engine goals |
| Social | Relationships, reputation toward player/factions |
| Memory | Durable events that affect future decisions and heart demons |
| Capabilities | Professions, known techniques |
| Location | Where they are; travel intents |
| Heaven's Will | Attention/pressure references when relevant |

### Behavior principles (proposed)

- Rivalries and betrayals emerge from goals + resources + fear/ambition—not random evil switches.
- Romance may exist under tone and content toggle rules ([GAME_VISION.md](GAME_VISION.md)).
- Important NPCs can learn techniques, hold offices, breakthrough, fail tribulations, and die; consequences persist.
- Simulation tiers may reduce tick rate for minor NPCs, but must not invent alternate cultivation formulas.

### MVP vs architecture

| MVP implementation | Long-term architecture |
|--------------------|------------------------|
| Handful of stub NPCs | Thousands of agents with sparse simulation tiers |
| Goals as simple tags | Full planners / need systems |
| No deep memory | Memory queries for dialogue and decisions |

## Out of scope / non-goals

- Full AI autonomy over NPC numerical cultivation outcomes.
- Writing a cast list of named legends in this pass.

## Unresolved design questions

- Simulation tiers (hero NPCs full fidelity vs background population aggregates)?
- How often off-screen NPCs breakthrough or die?
- Memory decay vs permanent critical memories?
- Player-killable major figures in MVP?

## Expansion notes

- Link NPCs to sects, techniques (known users), and economy roles.
- Related: [SECTS.md](SECTS.md), [ECONOMY.md](ECONOMY.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [TRIBULATIONS.md](TRIBULATIONS.md), [HEAVENS_WILL.md](HEAVENS_WILL.md), [AI_SYSTEM.md](AI_SYSTEM.md), [WORLD_GENERATION.md](WORLD_GENERATION.md).
