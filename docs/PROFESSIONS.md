# Professions

## Purpose

Detailed design of the **profession system** as the support economy of work and skill—strictly separate from cultivation personal power—scaled for many professions, recipes/jobs, and reputation channels while remaining learnable by any background.

---

## Confirmed design

| Rule | Source |
|------|--------|
| Cultivation and profession are **separate** | CULTIVATION_SYSTEM / GAME_PRINCIPLES |
| Profession earns **resources, reputation, money, influence, knowledge** | GAME_VISION |
| Cultivation determines **personal power** | GAME_VISION |
| Systems **support each other**; neither replaces the other | GAME_PRINCIPLES |
| Backgrounds seed opportunity; **never prevent** other professions | BACKGROUNDS |
| Player may later learn **every profession** | BACKGROUNDS |
| MVP: at least one minimal earn action; architecture for many professions | MVP_SCOPE |
| Engine authority over money/inventory/outcomes | AI_BOUNDARIES |

---

## Proposed design (detailed)

### 1. What a profession is

**Proposal:** A profession is a **progress track** (rank/XP) plus access to **jobs** and **recipes** that convert time/skill into the confirmed reward types. It is **not** a class and **not** a cultivation realm.

```mermaid
flowchart LR
  bg[BackgroundSeedSkills]
  prof[ProfessionRanks]
  job[JobsAndRecipes]
  out[Resources_Money_Reputation_Influence_Knowledge]
  cult[CultivationCostsAndPractice]
  bg -->|"boosts early ranks only"| prof
  prof --> job
  job --> out
  out -->|"funds and enables"| cult
```

### 2. Separation invariant (hard)

| Allowed | Forbidden |
|---------|-----------|
| Pills/gear/money that **enable** cultivation | Profession rank substituting for major realm in CPI |
| Reputation unlocking teachers or auctions | “Alchemist class” that cannot learn smithing |
| Alchemy **techniques** in the encyclopedia granting craft efficiency | Manual that grants +1 major realm effectively |

Profession-linked manuals are **technique catalog entries** ([TECHNIQUES.md](TECHNIQUES.md)) whose effect bundles primarily target craft/medicine/trade—not realm gaps.

**Profession → Dao:** every profession should eventually be able to ripen into a Dao of understanding ([DAO_SYSTEM.md](DAO_SYSTEM.md)). That ripening does not convert profession rank into combat realm power.

### 3. Data model

**Proposal:**

| Entity | Role |
|--------|------|
| `profession` | Catalog: id, name, description, linked skill tags |
| `actor_profession` | Per actor: profession_id, rank, xp/progress |
| `job` / `recipe` | Data: inputs, time, outputs, required rank, site tags |
| `profession_reputation` | Local standing with craft circles / halls ([REPUTATION.md](REPUTATION.md))—not a global meter |

Multiple `actor_profession` rows per actor are allowed (polymath careers).

**Tradeoff — one active profession vs many parallel ranks**

| Approach | Pros | Cons |
|----------|------|------|
| Single active profession | Clear fantasy; easy UI | Fights “learn every profession” |
| **Parallel ranks, soft time conflict (proposed)** | Matches confirmed freedom; realistic opportunity cost | Must budget time so Boundless Foundation + all crafts isn’t free |

**Decision lean:** Parallel ranks; **time** is the scarce shared resource (and cultivation already consumes time heavily on Boundless Foundation).

### 4. Skill tags (bridge from backgrounds)

**Proposal:** Backgrounds grant **skill tags / starting skill ranks** (e.g. `appraisal`, `herb_safety`, `forge_basics`). Professions **consume** those tags as XP discounts or unlocked starter jobs—not as exclusive keys.

Example: Alchemist's Apprentice starts faster in Alchemy but a Hunter can still open Alchemy at full cost.

**Tradeoff — soft skills vs hard profession XP only**

| Approach | Pros | Cons |
|----------|------|------|
| XP-only professions | Simple | Backgrounds feel disconnected |
| **Skill tags feed professions (proposed)** | Matches BACKGROUNDS categories; still non-locking | Needs a modest shared taxonomy |

Keep the taxonomy **small and extensible** (dozens of tags, not thousands).

### 5. Reward vector (confirmed types as explicit outputs)

Every job/recipe output is an engine bundle drawn from:

| Output | Examples of use |
|--------|-----------------|
| Resources | Herbs, ores, beast parts → cultivation / crafting inputs |
| Money | Mundane coin / spirit currency ([ECONOMY.md](ECONOMY.md)) |
| Reputation | Local craft circle standing |
| Influence | Favors with sect offices / officials (long-term) |
| Knowledge | Unlocks encyclopedia entries, maps, recipe discovery flags |

**Proposal:** Jobs declare outputs explicitly; AI narration does not invent payouts.

### 6. Rank progression

**Proposal:** Coarse ranks (e.g. Novice → Apprentice → Journeyman → Expert → Master → Grandmaster)—**names provisional**. Rank gates recipes and quality tiers.

Quality of output can scale with rank + linked technique mastery, still engine-resolved (spoilage/failure rules unresolved).

### 7. Starter profession families (catalog seeds, not exhaustive lore)

Aligned with backgrounds and long-term vision; each is a **profession_id**, not a class:

| profession_id (provisional) | Early jobs (examples) | Natural background affinity |
|-----------------------------|------------------------|-----------------------------|
| commerce | Haggle errands, consignments | Merchant's Child |
| alchemy | Assist refining, herb prep | Alchemist's Apprentice |
| smithing | Repair, basic forging | Blacksmith's Apprentice |
| hunting | Hunt contracts, material gather | Hunter |
| scholarship | Copying, research assists | Scholar |
| farming | Field labor, surplus sales | Farmer |
| medicine | Treat minor injuries | Doctor |
| streetcraft | Urban odd jobs, info runs | Street Urchin |
| beastkeeping | Stable work, escort beasts | Beast Keeper |
| administration | Clerical / etiquette errands | Minor Noble |

Players may open any track later. Affinity = discount/seed only.

**MVP implementation proposal:** ship **one** generic `labor` earn job plus **optional** one affinity job based on background—or simply one `labor` job that pays money/resources while architecture still defines the profession table. Prefer defining the catalog skeleton even if only `labor` + `alchemy` are playable.

### 8. Interaction with cultivation time and Boundless Foundation

**Proposal:**

- Profession work advances world time like cultivation practice.
- Boundless Foundation characters **need** profession/economy more (higher sinks)—profession is the support path, not a bypass.
- No profession that “refunds” tribulation outcomes.

**Tradeoff — automatic AFK income vs active jobs**

| Approach | Pros | Cons |
|----------|------|------|
| Heavy AFK passive | Convenience | Weakens agency; softens scarcity |
| **Active jobs with optional long commissions (proposed)** | Fits 15–60 min sessions and marathons | Needs good job UX |

Commissions (start job → return later) help short sessions feel productive without passive cheat income.

### 9. Influence and sects/economy (architectural hooks)

- Reputation/influence outputs feed [SECTS.md](SECTS.md) entry and [ECONOMY.md](ECONOMY.md) auction access later.
- Do not require full faction sim in MVP; store the **fields** so later systems consume them.

### 10. MVP vs long-term architecture

| Concern | MVP implementation | Long-term architecture |
|---------|--------------------|------------------------|
| Playable jobs | ≥1 earn action | Many professions/recipes |
| Ranks | Single rank or 2–3 coarse ranks | Full ladder |
| Outputs | Money + resources (reputation optional) | Full five-vector + influence sinks |
| Parallel professions | May track only one XP bar but schema allows many | Polymath careers |
| Failures | Optional | Spoilage, botches, lawsuits |

---

## Tradeoff summary (professions)

1. **Parallel profession ranks + time scarcity** over single-class profession → honors “learn everything.”  
2. **Skill tags as soft affinity** over hard locks → backgrounds matter without destiny.  
3. **Explicit output vectors** over narrative loot → engine authority.  
4. **Profession ≠ CPI** enforced via effect policy shared with techniques → preserves cultivation primacy.  
5. **Active/commission jobs** over strong AFK passive → short-session progress without idle exploits.

---

## Out of scope / non-goals

- Full recipe encyclopedias in this pass.
- Turning any profession into a combat class.
- Naming every material and pill.
- Implementation code.

---

## Unresolved design questions

1. Exact rank ladder names and count?
2. Shared skill-tag taxonomy (first draft list)?
3. MVP: only `labor`, or labor + background affinity job?
4. Crafting failure/spoilage model?
5. Can profession rank require minimum cultivation realm for high tiers (without becoming class gates)?
6. How strongly does commerce influence early Boundless Foundation sustainability?
7. Faction-specific profession reputations vs global craft fame?
8. Relation between alchemy profession rank and alchemy **technique** mastery—stacked how?

---

## Expansion notes

- Recipes/jobs should reference item ids and `technique_id` requirements where manuals matter.
- Caravans/auctions later consume the same money/resource outputs ([ECONOMY.md](ECONOMY.md)).
- Related: [BACKGROUNDS.md](BACKGROUNDS.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [TECHNIQUES.md](TECHNIQUES.md), [REALMS.md](REALMS.md), [DATABASE.md](DATABASE.md), [MVP_SCOPE.md](MVP_SCOPE.md).
