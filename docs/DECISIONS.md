# Decisions

## Purpose

Records locked implementation decisions so code and docs stay aligned. Prefer updating this file when a milestone resolves an open design question.

---

## Milestone 2 — Character creation and saves

| Decision | Choice |
|----------|--------|
| Save storage | One SQLite database (`saves/game.db`) holds **many** save worlds as rows sharing a schema. |
| Save scope | Each save eventually owns the entire persistent world for that run (player, inventory, events today; NPCs, sects, world state later). |
| Delete | Soft-delete (`deleted_at`). Permanent IDs are never reused. Explicit confirmation required. |
| Background selectable set (M2) | Data files only: **Merchant Family**, **Alchemist's Apprentice**, **Hunter**. Adding a background = add/validate a data file (no engine code change). |
| Background meaning | Pre-game **life history** stored as structured seed data—not a class, not destiny. Seeds are not simulated in M2. |
| Personality | Five universal questions. Persist **answers only**. No traits, Dao, or alignment assignment at creation. |
| Boundless Foundation | Not offered at creation. New characters start on the **ordinary** cultivation path. Story event comes later. |
| Money (M2) | Single integer field `money_copper` (mundane coin). |
| Active save | Cookie `active_save_id` after create/load. |
| IDs | UUID strings for persistent rows (`EntityMixin`). |

---

## Milestone 3 — Opening story + first cultivation loop

| Decision | Choice |
|----------|--------|
| Story engine | Data-driven JSON nodes; authoritative `story_progress.current_node_id`. |
| Anomaly trigger | First **breakthrough attempt** when qi/progress thresholds met — **not** a fixed practice-session count. |
| Anomaly presentation | Mystery / unexplained stall — not talentless or broken; investigations before Elder Yun Mei. |
| Revealer (M3) | **Elder Yun Mei**, Verdant Gate Foundation Hall — single authored NPC for this slice. |
| Boundless framing | Ancient path, openly taught once, abandoned for cost/difficulty; incomplete manuscripts; obsolete in modern doctrine. |
| Sect (M3) | **Verdant Gate Sect** (`sect_verdant_gate`) on Jade Ridge. |
| Cultivation methods | **Absorb Qi**, **Stabilize Foundation**, **Calm the Mind** — nearly identical M3 mechanics; establishes UI architecture. |
| Path lifecycle | `path_status`: `provisional` → `confirmed_ordinary` \| `confirmed_boundless`; permanent after choice. |
| World clock | `game_saves.world_day` is the simulation clock (`engine/time.py`). Advanced by travel effects, cultivation sessions, and (later) events. Playtime is separate telemetry. |
| M2 save bootstrap | First play load creates `story_progress` at background entry node. |
| Deferred from M3 | Profession earn, technique records, combat, full sect sim (later milestones). |
| Schema authority | **Alembic only** for production/dev DB. `create_app` must never call `create_all`. |
| Migration 0003 | **Idempotent** upgrades (skip existing columns/tables) so SQLite non-transactional DDL drift can recover. |
| Phase 1 cultivation framework | Data-driven realms/stages; meters: Qi, progress, comprehension, foundation stability; no realm breakthrough yet. |
| Second realm naming | **Qi Gathering** (`qi_gathering`) replaces earlier doc name Qi Condensation for the Phase 1 overhaul. |
| Foundation meters | `foundation_stability` (0–100) is the play meter; `foundation_quality` (1–6) remains the legacy Boundless/story tier, derived upward from stability via `max(derived, stored)`. |
| Phase 2 active sessions | Data-driven Cautious / Balanced / Aggressive methods; each session costs 1 world day + playtime; injectable RNG; no stage/realm advance from sessions. |
| Cultivation service | `CultivationService` owns session persistence; story hall still routes through `apply_story_action`. |
| Phase 3 breakthroughs | Data-driven stage readiness/chance/attempt in `engine/breakthroughs.py`. Provisional opening anomaly stays in `cultivation_path` via adapter. Ordinary opening Early→Middle remains story-gated on path commit. Peak→Qi Gathering Early is the only realm hop implemented. |
| Phase 4 roadmap | Event engine foundation for a dynamic world (not cultivation mechanics). Next: Location 5a–5c (shipped), then Modifier Framework **6a** → stub **6b** → Techniques **6c**, Spiritual Roots (7), Alchemy (8), NPCs/factions (9), Combat (10), World sim (11), AI story arcs (12). Professions deferred until after Locations/Techniques/Roots. |
| Breakthrough deferrals | Partial success, damaged foundations, and unique tribulations remain architecture hooks only until core systems are complete. |
| Foundation Establishment | Intentionally locked; polish Body Tempering + Qi Gathering first. |
| Actor model | Player cultivation remains a compatibility layer until NPCs/sects; new systems use opaque `actor_id`. |
| Time | New systems use centralized `engine/time.py` (`world_day`). Playtime is telemetry only. |
| AI authority | Backend owns all permanent mechanics; AI is presentation only. |

### Phase 4a — Event engine core (shipped)

| Decision | Choice |
|----------|--------|
| Selection | At most one event per trigger: eligibility → weighted pick → activation chance. Structured `no_event` when nothing fires. `EventTriggerBatch` allows future multi-event without changing saved row shapes. |
| `players.actor_id` | Opaque UUID; backfilled from `players.id`. Unique index. Event engine does not assume actors come from the players table. |
| RNG | `game_saves.world_rng_counter` is separate from `players.cultivation_rng_counter` so cultivation determinism stays intact. Event rolls require injected `random.Random` only. |
| Live hooks | Not in 4a. First live hook (4b) = after successful cultivation session, same DB transaction. |
| Phase 4b live hook | After successful cultivation session (story hall + CultivationService), same DB transaction. Provisional path seeds are ineligible. No events on blocked/rejected requests or UI render. |
| Seed content (4b) | 3 cultivation ambient + 1 setback (`after_cultivation_session`); 1 exploration stub (`after_story_travel` only, not live). |
| Schema extras | Optional `context` tag bags; optional `ai_prompt_key` (template ref only — no AI behavior). |
| Phase 4c tooling | Startup catalog validation; CLI `ai-adventure-events`; debug routes when `debug=True`; dry-run simulation + stats. |
| Phase 4c library | Expanded ambient cultivation, environment, discovery, npc_encounter; combat stub on `manual_debug` only. |
| History vs cooldown | `event_log` immutable history; `event_cooldowns` mutable current state only. |
| Migration | `0007_event_engine`. |
| Travel hook (was 4d) | Deferred into Location Phase **5b** with WorldClock unification. |

### Phase 5a — Location catalog + presence (shipped)

| Decision | Choice |
|----------|--------|
| Content organization | Modular **world packs** under `data/world/packs/` with `world_manifest.json`; merged into one catalog at load. |
| Pack set (5a) | `opening_homelands`, `jade_ridge`, `verdant_gate` (`depends_on: jade_ridge`). |
| Catalog authority | Location existence + `display_name` from catalog; saves store `current_location_id` + denormalized name cache. |
| Presence | Table `location_presence` — discovery/visit mutable state only. |
| Reserved mechanics | weather/spiritual/danger/resources/npc/event/cultivation/environment tags + `technique_tags` / `technique_ids` for Phase 6c. |
| Presentation fields | `music` / `artwork` / `ambience` — never mechanical. |
| Story migration | Existing story/background/sect location ids catalogued; `set_location` resolves names from catalog. |
| Startup validation | `validate_location_catalog_on_startup` (default true). |
| Migration | `0008_locations`. |
| Non-goals (5a) | No freeroam UI, travel graph live use, explore actions, or procedural gen. |

### Phase 5b — Travel + WorldClock + live travel events (shipped)

| Decision | Choice |
|----------|--------|
| LocationService | Sole orchestrator for location mutations and play-time world-day advances from story/travel. |
| Travel graph | Authored `travel` edges on location catalog; story and free travel share the same edges. |
| Free travel | `LocationService.travel` — requires public edge; uses edge `days`. |
| Story movement | `LocationService.apply_story_transition` — same edges; day cost from story clock delta. |
| WorldClock | Cultivation, events, and travel advance `world_day` only via `advance_world_days` / `SaveRepository.advance_world_day`. |
| Live hook | `EventService.run_after_story_travel` after successful travel-like relocates (`mode=travel` or `days > 0`). |
| Reserved edge fields | method, danger, restrictions, cost, visibility, hidden_route, unlock_requirements. |
| Non-goals (5b) | Map UI, overworld, explore actions, procedural gen, travel combat. |

### Phase 5c — Location actions (shipped)

| Decision | Choice |
|----------|--------|
| Naming | “Location actions,” not open-world exploration. |
| Catalog | `data/world/action_catalog.json`; sites list offered action ids. |
| Pipeline | `LocationService.perform_action` → WorldClock → event trigger → persist. |
| Implemented | `explore` (1 day, `after_explore`), `inspect` (0 days, `after_inspect`). |
| Events | `location_actions.json` uses real `requirements.location_ids`. |
| UI | Play scene panel + `POST /play/{save_id}/location-action`. |
| Reserved actions | cultivate/rest/talk/train/leave/travel/study/trade present, not executable. |
| Non-goals | Procedural explore, map UI, travel combat, NPC schedules. |

### Phase 6a — Modifier Framework design lock

| Decision | Choice |
|----------|--------|
| Framework role | Answer only: “What mechanical influences apply to this actor right now?” Not an ability system, scripting engine, or mutation pipeline. |
| Ownership | Engine owns aggregation, validation, caps, context filtering, stacking, snapshots. Content supplies data only. Unknown effect types fail validation. |
| Separation forever | **Intent** (attempt) ≠ **Modifier** (bias calculation) ≠ **Mutation** (permanent state change). Event/story apply-effects stay mutations. |
| Aggregation (Phase 6) | Sum flats → multiply mults → clamp to engine caps; flags OR. No diminishing returns, priority, exclusive groups, or custom stacking. |
| Snapshot | Always ephemeral; never persisted. Recompute from active sources. |
| First source | Techniques (Phase **6c**). Later: roots, gear, statuses, sect bonuses, location auras — same allowlisted types. |
| Boundless | **Out of Phase 6.** Path multipliers stay in cultivation helpers; `cultivation_path` source kind reserved only. |
| Milestone order | **6a** docs lock → **6b** engine stub + tests (no gameplay change) → **6c** techniques + session wiring. Stop after each for review. |
| Canonical doc | [MODIFIER_FRAMEWORK.md](MODIFIER_FRAMEWORK.md). |

### Phase 6b — Modifier Framework engine stub (shipped)

| Decision | Choice |
|----------|--------|
| Module | `engine/modifiers.py` — pure aggregate; no DB, no services, no consumers |
| Type registry | `data/modifiers/effect_types.json` — each type declares `value_type`, `aggregation`, caps, `allowed_contexts` |
| Bundles | `data/modifiers/effect_bundles.json` — validated against registry (fixture bundle only) |
| Aggregation | Per-type registry rule: sum flats / multiply mults / OR flags; then clamp |
| Snapshot | `numbers` + `flags` + `contributions` audit; ephemeral only |
| Non-goals | No migrations, no persistence, no gameplay wiring, Boundless untouched |

### Phase 6c — Techniques as first modifier source (shipped)

| Decision | Choice |
|----------|--------|
| Catalog | `data/techniques/techniques.json` — 3 starters: Steady Practice, Qi Absorption, Foundation Guard |
| Bundles | One category each: progress mult, Qi mult, stability flat |
| Mastery | Table `technique_mastery` (`0009`); known + equipped + rank; learn auto-equips |
| Consumer | Cultivation sessions only — receive `ModifierSnapshot`; never read technique/mastery/bundles |
| Breakthroughs | **Not wired** in 6c (follow-up consumer milestone) |
| Boundless | Still outside modifiers |
| UI | Play scene techniques panel + `POST /play/{save_id}/techniques/learn` |

### Phase 6c follow-up — Breakthrough ModifierSnapshot consumer (shipped)

| Decision | Choice |
|----------|--------|
| Consumer allowlists | Each consumer declares supported effect types; unsupported snapshot keys are **ignored** via `consumer_number` |
| Sessions | `SESSION_SUPPORTED_EFFECT_TYPES` |
| Breakthroughs | `BREAKTHROUGH_SUPPORTED_EFFECT_TYPES` = `{breakthrough_chance_flat}` only |
| Wiring | Readiness + attempt accept ephemeral snapshot; Boundless multipliers stay outside framework |
| Starter art | `tech_threshold_focus` (+0.03 breakthrough chance) validates the path |
| Not wired | Event selection bias (6d), combat |

### Phase 6d — Event Selection Bias consumer

| Decision | Choice |
|----------|--------|
| Naming | **Event Selection Bias**, not “Event Eligibility”. Hard eligibility stays in Event Engine. |
| Soft bias | Event Engine consumes ephemeral `ModifierSnapshot` for weights, activation chance, optional flags. |
| Mutations | Remain entirely in Event Engine (`modify_cultivation`, grants, flags, clock, persistence). |
| Effect types | Generic `weight_mult` + `chance_flat` (+ existing `flag`) — **not** `event_weight_mult` / `event_activation_chance_flat`. |
| Context metadata | `applies_to: ["world_event"]` + optional `category` matching `EventTemplate.category`; omit category for global bias. |
| Params shape | Keep registry `param_key` (`params.mult` / `params.flat`); no free-form `value` field. |
| Aggregation | Bucket by `(effect_type_id, category)`; snapshot exposes uncategorized `numbers` + `categorized_numbers`. |
| Composition | Effective weight = catalog × global `weight_mult` × category `weight_mult`. Effective chance = clamp(catalog + global `chance_flat` + category `chance_flat`). |
| Allowlist | `EVENT_SUPPORTED_EFFECT_TYPES`; unsupported keys ignored. |
| Location dicts | Do **not** read `event_weight_modifiers` in 6d (avoid dual bias channels). Future location auras emit the same generic types. |
| Order | 6d-0 docs → 6d-1 wiring/tests → 6d-2 proving technique+event. Stop for review before Phase 7 Roots. |

### Phase 7 — Spiritual Roots (second modifier source)

| Decision | Choice |
|----------|--------|
| Role | Second Modifier Framework **source** — not a new consumer |
| Catalog | `data/cultivation/spiritual_roots.json` + effect bundles |
| Persistence | `spiritual_root_ownership` (`0010`); catalog authority for definitions |
| Emission | Ownership → `EffectInstance` (`source_kind=spiritual_root`) → same aggregate path as techniques |
| Snapshot builder | Combines technique mastery + root ownership before `aggregate(activity)` |
| Consumers | Unchanged: sessions, breakthroughs, event selection bias |
| Starter grant | New characters awaken `root_wood_steady` |
| Non-goals | Equipment, auras, buffs, combat, AI, framework redesign |

Canonical doc: [SPIRITUAL_ROOTS.md](SPIRITUAL_ROOTS.md).

### Phase 8 — Alchemy (third modifier source)

| Decision | Choice |
|----------|--------|
| Role | Third Modifier Framework **source** — EffectBundles only |
| Persistence | `alchemy_recipe_ownership` (`0011`) |
| Non-goals | Full crafting economy, temporary pill statuses as separate system |

### Phase 9a–9b — NPC / Sect foundation (vertical slice)

| Decision | Choice |
|----------|--------|
| Catalogs | Pack-local `npcs.json` / `sects.json` under world packs |
| Identity | Catalog-only; story `spawn_npc` payload is `{npc_id}` |
| Mutable state | `npc_world_state` (`0012`); row id = opaque actor_id |
| Vertical slice | Spawn → greet → relationship delta → save/reload |
| Out of scope | AI dialogue, NPC cultivation sim, schedules, combat, reputation graph, new modifier sources |
| Next | 9c expand interactions; 9d sect standing |

Canonical doc: [NPCS.md](NPCS.md).

### Schema drift note (Milestone 3 repair)

Older builds called ``Base.metadata.create_all()`` on app startup. That created tables **without** ``alembic_version`` history. Later, stamping to ``0002`` and running ``0003`` under SQLite could apply DDL that survived even if Alembic did not record head—re-running then failed with ``duplicate column name: world_day``. Fix: remove startup ``create_all``, make ``0003`` idempotent, and keep tests on isolated temp DBs only.

---

## Expansion notes

- Related: [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [BACKGROUNDS.md](BACKGROUNDS.md), [DATABASE.md](DATABASE.md), [ARCHITECTURE.md](ARCHITECTURE.md), [PLAYER_IDENTITY.md](PLAYER_IDENTITY.md), [OPENING_STORY.md](OPENING_STORY.md), [EVENT_ENGINE.md](EVENT_ENGINE.md), [LOCATIONS.md](LOCATIONS.md), [MODIFIER_FRAMEWORK.md](MODIFIER_FRAMEWORK.md), [TECHNIQUES.md](TECHNIQUES.md), [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md).
