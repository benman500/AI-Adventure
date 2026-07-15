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

## Proposed layout (informational)

How the stack maps to existing folders (not gameplay code):

| Concern | Likely home |
|---------|-------------|
| Engine + FastAPI app | `src/` |
| Tests | `tests/` |
| SQLite files / saves bridge | `saves/` and/or configured DB path via pydantic-settings |
| Jinja2 templates + static CSS/JS | under `src/` presentation package or `assets/` for static |
| Prompt/style assets | `prompts/` (when AI is enabled) |
| Design truth | `docs/` |

Exact package names remain an implementation detail to be approved at coding start.

---

## Out of scope / non-goals

- Implementing application code in this pass
- Choosing host/deploy targets beyond local MVP
- Shipping Ollama/OpenAI integrations in MVP (architecture: Narrator interface only)

---

## Unresolved design questions

1. Single-process FastAPI serving Jinja2 vs separate static asset layout conventions?
2. SQLite file location convention (one DB under `saves/` vs data/)?
3. Async SQLAlchemy engine usage vs sync for MVP simplicity?
4. Minimum Python patch version within 3.14+ for CI?

---

## Expansion notes

- Add Narrator implementations (Ollama, OpenAI-compatible) behind the same interface without changing engine authority.
- Docker may be reconsidered **after** MVP; it remains forbidden during MVP.
- Related: [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md), [DATABASE.md](DATABASE.md), [MVP_SCOPE.md](MVP_SCOPE.md).
