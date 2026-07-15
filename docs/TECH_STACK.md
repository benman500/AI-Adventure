# Tech Stack

## Purpose

Locks the **approved technology stack** for this project. Gameplay implementation must follow this document. Stack choice is no longer an open design question.

See also: [GAME_PRINCIPLES.md](GAME_PRINCIPLES.md), [AI_BOUNDARIES.md](AI_BOUNDARIES.md), [DATABASE.md](DATABASE.md), [ARCHITECTURE.md](ARCHITECTURE.md), [MVP_SCOPE.md](MVP_SCOPE.md).

---

## Confirmed design

### Programming language

- **Python 3.14+**

### Backend

- **FastAPI**

### Database

- **SQLite**

### ORM

- **SQLAlchemy 2**

### Database migrations

- **Alembic**

### Validation

- **Pydantic**

### Configuration

- **pydantic-settings**

### Frontend

- **HTML**
- **CSS**
- **Vanilla JavaScript**
- **Jinja2** templates

### Testing

- **pytest**
- **pytest-cov**

### Version control

- **Git**

### AI (presentation layer only)

- **Abstract Narrator interface** (engine talks to an interface; implementations are swappable)
- **Ollama** support later
- **OpenAI-compatible APIs** later

Game mechanics must **function without AI**. Stub/template narration is required when no provider is configured.

### Authority (restated)

- The **game engine** is authoritative for all mechanics and persistent state.
- **AI only narrates** (dialogue, descriptions, flavor). AI never decides outcomes or writes the database.
- Align with [AI_BOUNDARIES.md](AI_BOUNDARIES.md) and [AI_SYSTEM.md](AI_SYSTEM.md).

---

## Confirmed restrictions

Do **not** introduce:

| Forbidden | Notes |
|-----------|--------|
| Django | Use FastAPI |
| Flask | Use FastAPI |
| React | Use HTML/CSS/vanilla JS + Jinja2 |
| Vue | Same |
| Angular | Same |
| Node.js | Backend is Python |
| Docker during MVP | Local/dev without container requirement for MVP |

---

## Confirmed layout (scaffold)

| Concern | Location |
|---------|----------|
| Engine + FastAPI app | `src/ai_adventure/` |
| Tests | `tests/` |
| SQLite default | `saves/game.db` (override with `AI_ADVENTURE_DATABASE_URL`) |
| Jinja2 + static CSS/JS | `src/ai_adventure/presentation/` |
| Prompt assets | `prompts/` (when AI providers are added) |
| Design truth | `docs/` |

**MVP defaults:** sync SQLAlchemy; StubNarrator; no Docker.

---

## Out of scope / non-goals

- Full gameplay systems in the initial scaffold
- Shipping Ollama/OpenAI integrations in MVP (Narrator interface + stub only)
- Docker during MVP

---

## Unresolved design questions

1. Async SQLAlchemy in a later phase?
2. CI Python exact micro-version within 3.14+?

---

## Expansion notes

- Add Narrator implementations (Ollama, OpenAI-compatible) behind the same interface without changing engine authority.
- Docker may be reconsidered **after** MVP; it remains forbidden during MVP.
- Related: [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md), [DATABASE.md](DATABASE.md), [MVP_SCOPE.md](MVP_SCOPE.md).
