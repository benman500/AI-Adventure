# Player Identity

## Purpose

Defines character-creation identity questioning and how answers are stored. Background remains **pre-game life history**, not destiny ([BACKGROUNDS.md](BACKGROUNDS.md)). Boundless path choice is a **story event**, not part of identity ([BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md)).

## Confirmed design (Milestone 2)

- Character creation includes **five universal personality questions** (data-driven: `data/identity/personality_questions.json`).
- The engine **stores answer ids only** on the player record.
- Creation does **not**:
  - assign permanent personality traits
  - decide the player's Dao
  - determine alignment / global good-evil
  - auto-select Boundless Foundation
- Future systems may interpret stored answers over time (dialogue lean, heart demons, affinity hints)—that interpretation is **out of Milestone 2**.
- Identity must **not** grant unique cultivation rules.

## Creation pipeline

1. Name  
2. Background (life-history seeds)  
3. Personality questions → persist raw answers  
4. Apply starting inventory/money/location/cultivation seed (ordinary path)  
5. Enter save — Boundless choice later via story event  

## Related

- [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [DECISIONS.md](DECISIONS.md), [DAO_SYSTEM.md](DAO_SYSTEM.md), [BOUNDLESS_FOUNDATION.md](BOUNDLESS_FOUNDATION.md).
