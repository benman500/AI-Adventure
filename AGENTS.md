# Cultivation RPG Agent Rules

## Required reading

Before editing anything, read:

- PROJECT_CONTEXT.md
- CURRENT_MILESTONE.md
- docs/ARCHITECTURE.md
- docs/DECISIONS.md
- docs/DEVELOPMENT_ROADMAP.md

Read additional system documentation relevant to the assigned task.

## Project laws

- The engine owns all mechanics.
- AI is presentation only.
- Catalogs define authored content.
- Saves contain mutable state only.
- Aspirations provide purpose by reading durable facts.
- Events provide authored surprise.
- Identity is a read-only presentation projection.
- Never invent a parallel progression system.
- Never create private calculation paths that bypass existing engines.
- Preserve the existing service and transaction boundaries.
- Keep existing gameplay working.

## Standard pipeline

Intent
→ Service
→ Validation
→ WorldClock when applicable
→ Engine rules
→ Event Engine
→ Persistence
→ Presentation

## Before editing

- Inspect the relevant implementation and tests.
- Confirm the task can be completed within its allowed scope.
- Stop if requirements are ambiguous.
- Do not reinterpret or expand the milestone.

## Testing

Run focused tests while working.

Before declaring completion, run:

python -m pytest -q

Do not delete, skip, weaken, or rewrite tests merely to make them pass.

## Forbidden without human approval

- Database migrations
- New architecture
- New dependencies
- Changes to deployment files
- Changes to secrets or environment files
- Changes to production databases
- Deleting migrations
- Rewriting Git history
- Pushing or merging
- Large unrelated refactors
- More than 25 changed files
- Modifying game rules during UI-only tasks

## Git

- Work only on the current agent branch.
- Never push.
- Never merge into main.
- Do not use git reset --hard.
- Do not delete untracked user files.

## Completion report

At completion, create or update:

automation/AGENT_REPORT.md

Include:

- Task completed
- Files changed
- Tests run
- Test results
- Remaining risks
- Anything requiring human review
