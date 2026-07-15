# AI Adventure

A persistent cultivation **world simulation** with AI narration—not a pure AI text adventure.

## Project Structure

```
.
├── assets/      # Static media (images, audio, etc.)
├── docs/        # Design notes, architecture, and documentation
├── prompts/     # AI prompt templates and system instructions
├── saves/       # Player save files (ignored by git)
├── src/         # Application source code
├── tests/       # Automated tests
├── .gitignore
└── README.md
```

## Design Documents

Core and systems docs live under `docs/`. Start with [GAME_PRINCIPLES.md](docs/GAME_PRINCIPLES.md), then [DESIGN_REVIEW.md](docs/DESIGN_REVIEW.md) before implementation.

| Document | Focus |
|----------|--------|
| [GAME_VISION.md](docs/GAME_VISION.md) | Product vision, tone, pacing |
| [GAME_PRINCIPLES.md](docs/GAME_PRINCIPLES.md) | Permanent design philosophy |
| [DESIGN_REVIEW.md](docs/DESIGN_REVIEW.md) | Pre-implementation doc audit |
| [CULTIVATION_SYSTEM.md](docs/CULTIVATION_SYSTEM.md) | Power, Boundless Foundation mechanics, shared ruleset |
| [BOUNDLESS_FOUNDATION.md](docs/BOUNDLESS_FOUNDATION.md) | Boundless story event, informed permanent choice |
| [REALMS.md](docs/REALMS.md) | Locked early realms |
| [DAO_SYSTEM.md](docs/DAO_SYSTEM.md) | Dao as understanding; profession→Dao |
| [TRIBULATIONS.md](docs/TRIBULATIONS.md) | Signature tribulations |
| [HEAVENS_WILL.md](docs/HEAVENS_WILL.md) | World balancing |
| [TECHNIQUES.md](docs/TECHNIQUES.md) | Technique encyclopedia |
| [PROFESSIONS.md](docs/PROFESSIONS.md) | Profession work |
| [BACKGROUNDS.md](docs/BACKGROUNDS.md) | Upbringing packages |
| [CHARACTER_CREATION.md](docs/CHARACTER_CREATION.md) | Creation flow |
| [PLAYER_IDENTITY.md](docs/PLAYER_IDENTITY.md) | Personality questions, traits, affinities |
| [SECTS.md](docs/SECTS.md) | Sect factions |
| [SECT_LIFE.md](docs/SECT_LIFE.md) | Living sect daily life |
| [REPUTATION.md](docs/REPUTATION.md) | Local opinion graph |
| [NPCS.md](docs/NPCS.md) | NPC goals and shared cultivation |
| [WORLD_MODEL.md](docs/WORLD_MODEL.md) | World entity vocabulary |
| [WORLD_GENERATION.md](docs/WORLD_GENERATION.md) | Authored/procedural content |
| [COMBAT.md](docs/COMBAT.md) | Combat; hidden CPI |
| [ECONOMY.md](docs/ECONOMY.md) | Markets and trade |
| [AI_SYSTEM.md](docs/AI_SYSTEM.md) / [AI_BOUNDARIES.md](docs/AI_BOUNDARIES.md) | AI pipelines and hard limits |
| [DECISIONS.md](docs/DECISIONS.md) | Locked implementation decisions |
| [DATABASE.md](docs/DATABASE.md) | Persistence architecture |
| [TECH_STACK.md](docs/TECH_STACK.md) | Locked language, backend, DB, frontend, AI |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layered runtime flow and responsibilities |
| [MVP_SCOPE.md](docs/MVP_SCOPE.md) | MVP vs architecture |
| [DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) | Phased delivery |

## Getting Started

Requires **Python 3.14+**. Milestone 2: character creation + multi-save persistence (no gameplay loop yet).

```bash
cd "AI- Adventure"
py -3.14 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
uvicorn ai_adventure.main:app --reload
```

Open http://127.0.0.1:8000 — use **New Game** / **Load Saves**.

Default SQLite file: `saves/game.db`. Override with `AI_ADVENTURE_DATABASE_URL`.

Migrations: `alembic upgrade head` (after install; `alembic/env.py` reads the same settings).

## Development Notes

- Layers: Browser → FastAPI → Services → Engine → Repositories → SQLAlchemy → SQLite ([ARCHITECTURE.md](docs/ARCHITECTURE.md)).
- AI only narrates completed outcomes; StubNarrator keeps mechanics online without AI.
- The world persists without the player; AI never mutates state or decides numerical outcomes.
- No global good/evil meter; reputation is local.
- Dao is understanding, not a combat stat; CPI is internal-only.
- MVP stays small; architecture anticipates the full vision.
