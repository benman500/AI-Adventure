# Realms

## Purpose

Permanent design of the cultivation **major realm / minor stage** ladder, locked early realms, power-gap expectations, cosmology layering, and scalable data for additional realms later. Component axes (Body, Qi, Soul, Dao, Foundation Quality) are defined in [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md).

---

## Confirmed design

| Rule | Notes |
|------|--------|
| Major realms + minor stages | Core structure |
| Enormous jump between major realms; exponential scaling | Design compass |
| ~50 peak of N ≈ 1 early of N+1 | Balance compass |
| Boundless Foundation high mastery may compete with ordinary early N+1 | Same rules for all actors |
| **Players and NPCs share one realm/cultivation ruleset** | No unique player realms math |
| Early ladder **locked** (permanent design) | See below |
| CPI (if used) is **internal only**—never shown to players as a number | Presentation uses realm/stage/quality cues |
| Engine-authoritative progression | AI does not decide |
| Lower worlds / higher immortal realms as cosmology | Access ≠ soft power reset |

### Locked early major realms (permanent)

| order_index | realm_id (stable) | display_name |
|------------:|-------------------|--------------|
| 1 | `body_tempering` | Body Tempering |
| 2 | `qi_condensation` | Qi Condensation |
| 3 | `foundation_establishment` | Foundation Establishment |
| 4 | `core_formation` | Core Formation |

These four are **confirmed permanent content**. They are no longer placeholders. Future realms append **above** `core_formation` (or reserve gaps in `order_index` only for deliberate inserts that do not rename these four).

---

## Proposed details

### Realms as data

Each realm: `realm_id`, `order_index`, `display_name`, `cosmology_layer`, `stage_scheme_id`. Adding realm 5+ is catalog growth. Players and NPCs reference the same ids.

### Uniform minor stages (proposed)

Default scheme `standard_4`: **early / mid / late / peak**. Applies to the locked early four; expected default for later realms unless an alternate scheme is explicitly added.

### Power model and hidden CPI

- Internal **Combat Power Index** may combine `order_index`, stage, path, Body/Qi/Soul/Dao/Foundation Quality, and bounded technique effects.
- **Never** display CPI (or any raw “combat power” integer) to the player.
- Player-facing: realm name, stage, qualitative foundation language, injuries/scars, rumors (“can pressure early Core Formation experts”), narration.

**Tradeoff** remains: numeric internals for the 50:1 compass vs player fantasy readability—solved by hiding numbers.

### Cosmology layers (proposed)

`cosmology_layer` gates habitat/ascension without resetting the order spine. Continuous `order_index` across lower → immortal bands (proposed lean from prior approval).

### Breakthroughs at peak → next realm

Major breakthroughs use the confirmed outcome vocabulary: success, failure, partial success, damaged foundations, unique tribulations ([TRIBULATIONS.md](TRIBULATIONS.md), [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md)).

### MVP vs architecture

| Concern | MVP | Long-term |
|---------|-----|-----------|
| Playable realms | Subset of the locked four (depth unresolved) | Full four + later catalog |
| Stage scheme | `standard_4` | Optional alternate schemes |
| CPI | Hidden internals | Same policy forever |
| Immortal bands | Not required playable | Appended realms + layers |

```mermaid
flowchart LR
  bt[BodyTempering] --> qc[QiCondensation]
  qc --> fe[FoundationEstablishment]
  fe --> cf[CoreFormation]
  cf --> later[LaterRealms]
```

---

## Tradeoff summary

1. **Lock early four** over endless placeholders → stable fiction and technique requirements.  
2. **Shared ruleset** for all actors → simulation integrity.  
3. **Hidden CPI** over visible scoresheets → xianxia presentation.  
4. **One spine + component axes** (in cultivation doc) over five rival ladders.

---

## Out of scope / non-goals

- Full immortal realm name list now.
- Visible combat-power HUD numbers.
- Player-only realm shortcuts.

---

## Unresolved design questions

1. How many of the locked four are reachable in MVP?
2. Exact hidden weights (stage, axes) into CPI?
3. Reserved `order_index` gaps between locked realms? (Recommend **no**—append after 4.)
4. Flavor aliases in dialogue vs strict display names?
5. Soft political caps vs hard engine caps on ascending past Core Formation on a given world?

---

## Expansion notes

- Technique `min_realm` requirements should use `realm_id` / `order_index` of these locked ids where relevant.
- Related: [CULTIVATION_SYSTEM.md](CULTIVATION_SYSTEM.md), [TRIBULATIONS.md](TRIBULATIONS.md), [COMBAT.md](COMBAT.md), [HEAVENS_WILL.md](HEAVENS_WILL.md), [TECHNIQUES.md](TECHNIQUES.md).
