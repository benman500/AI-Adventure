"""Engine constants (no magic numbers in rules code)."""

# Starting cultivation seed (shared ruleset; no simulation in Milestone 2).
STARTING_CULTIVATION_PATH = "ordinary"
STARTING_REALM_ID = "body_tempering"
STARTING_STAGE_ID = "early"
STARTING_BODY = 1
STARTING_QI = 1
STARTING_SOUL = 1
STARTING_DAO = 1
STARTING_FOUNDATION_QUALITY = 1

# Path status lifecycle (Milestone 3).
PATH_STATUS_PROVISIONAL = "provisional"
PATH_STATUS_CONFIRMED_ORDINARY = "confirmed_ordinary"
PATH_STATUS_CONFIRMED_BOUNDLESS = "confirmed_boundless"

# Anomaly lifecycle.
ANOMALY_STATE_NONE = "none"
ANOMALY_STATE_TRIGGERED = "triggered"
ANOMALY_STATE_RESOLVED = "resolved"

# Breakthrough readiness.
BREAKTHROUGH_NOT_READY = "not_ready"
BREAKTHROUGH_READY = "ready"
BREAKTHROUGH_ATTEMPTED = "attempted"

# Cultivation path identifiers.
CULTIVATION_PATH_ORDINARY = "ordinary"
CULTIVATION_PATH_BOUNDLESS = "boundless"

# Milestone 3 / Phase 1 cultivation thresholds (deterministic; not session-count triggers).
STARTING_QI_RESERVE_MAX = 10
STARTING_REALM_COMPREHENSION = 0
STARTING_FOUNDATION_STABILITY = 50
BREAKTHROUGH_QI_THRESHOLD = 10
BREAKTHROUGH_PROGRESS_THRESHOLD = 70
CULTIVATION_PROGRESS_MAX = 100
REALM_COMPREHENSION_MAX = 100
FOUNDATION_STABILITY_MAX = 100
FOUNDATION_STABILITY_MIN = 0

# Cultivation method yields:
# method_id -> (qi_gain, progress_gain, comprehension_gain, foundation_stability_delta)
CULTIVATION_METHOD_ABSORB_QI = "absorb_qi"
CULTIVATION_METHOD_STABILIZE_FOUNDATION = "stabilize_foundation"
CULTIVATION_METHOD_CALM_MIND = "calm_mind"

CULTIVATION_METHOD_YIELDS: dict[str, tuple[int, int, int, int]] = {
    CULTIVATION_METHOD_ABSORB_QI: (4, 25, 2, 0),
    CULTIVATION_METHOD_STABILIZE_FOUNDATION: (3, 27, 1, 3),
    CULTIVATION_METHOD_CALM_MIND: (5, 22, 4, 1),
}

# Post-path mechanical multipliers.
ORDINARY_BREAKTHROUGH_THRESHOLD_MULTIPLIER = 1.0
ORDINARY_RESOURCE_COST_MULTIPLIER = 1.0
ORDINARY_PROGRESS_MULTIPLIER = 1.0

BOUNDLESS_BREAKTHROUGH_THRESHOLD_MULTIPLIER = 3.0
BOUNDLESS_RESOURCE_COST_MULTIPLIER = 2.0
BOUNDLESS_PROGRESS_MULTIPLIER = 0.5

# Character naming.
MIN_CHARACTER_NAME_LENGTH = 1
MAX_CHARACTER_NAME_LENGTH = 64

# Event types.
EVENT_TYPE_CHARACTER_CREATED = "character_created"
EVENT_TYPE_STORY_ENTERED = "story_entered"
EVENT_TYPE_STORY_ACTION = "story_action"
EVENT_TYPE_CULTIVATION_PRACTICE = "cultivation_practice"
EVENT_TYPE_BREAKTHROUGH_READINESS = "breakthrough_readiness"
EVENT_TYPE_BREAKTHROUGH_ATTEMPT = "breakthrough_attempt"
EVENT_TYPE_CULTIVATION_ANOMALY = "cultivation_anomaly_triggered"
EVENT_TYPE_PATH_CHOICE_ORDINARY = "path_choice_ordinary"
EVENT_TYPE_PATH_CHOICE_BOUNDLESS = "path_choice_boundless"
EVENT_TYPE_BREAKTHROUGH_SUCCESS = "breakthrough_success"
EVENT_TYPE_WORLD_EVENT_RESOLVED = "world_event_resolved"
EVENT_TYPE_TRAVEL_RESOLVED = "travel_resolved"
EVENT_TYPE_LOCATION_ACTION = "location_action_resolved"
EVENT_TYPE_TECHNIQUE_LEARNED = "technique_learned"
EVENT_TYPE_SPIRITUAL_ROOT_AWAKENED = "spiritual_root_awakened"
EVENT_TYPE_ALCHEMY_RECIPE_AWAKENED = "alchemy_recipe_awakened"
EVENT_TYPE_NPC_INTERACTION = "npc_interaction"

# Story flags.
FLAG_LESSON_COMPLETE = "lesson_complete"
FLAG_BREAKTHROUGH_READY = "breakthrough_ready"
FLAG_ANOMALY_TRIGGERED = "anomaly_triggered"
FLAG_INVESTIGATION_COMPLETE = "investigation_complete"
FLAG_REVELATION_SEEN = "revelation_seen"
FLAG_PATH_CONFIRMED = "path_confirmed"

# Sect / content ids.
SECT_VERDANT_GATE_ID = "sect_verdant_gate"
RANK_OUTER_DISCIPLE = "outer_disciple"

ACTIVE_SAVE_COOKIE = "active_save_id"
DELETE_CONFIRMATION_VALUE = "DELETE"

# Realm display names (fallback; prefer engine.realms catalog).
REALM_DISPLAY_NAMES: dict[str, str] = {
    "body_tempering": "Body Tempering",
    "qi_gathering": "Qi Gathering",
    "qi_condensation": "Qi Gathering",  # legacy alias from pre-Phase-1 docs
    "foundation_establishment": "Foundation Establishment",
    "core_formation": "Core Formation",
}

STAGE_DISPLAY_NAMES: dict[str, str] = {
    "early": "Early",
    "middle": "Middle",
    "mid": "Middle",  # legacy Milestone 3 id
    "late": "Late",
    "peak": "Peak",
}

FOUNDATION_QUALITY_BANDS: list[tuple[int, str]] = [
    (1, "Fragmented"),
    (2, "Flawed"),
    (3, "Stable"),
    (4, "Solid"),
    (5, "Near-flawless"),
    (6, "Flawless"),
]
