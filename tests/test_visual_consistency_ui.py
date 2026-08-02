"""Presentation checks for player-facing visual consistency (UI-only)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAY_CSS = (
    REPO_ROOT / "src" / "ai_adventure" / "presentation" / "static" / "css" / "main.css"
)
PLAY_SCENE_TEMPLATE = (
    REPO_ROOT
    / "src"
    / "ai_adventure"
    / "presentation"
    / "templates"
    / "play_scene.html"
)
HOME_TEMPLATE = (
    REPO_ROOT / "src" / "ai_adventure" / "presentation" / "templates" / "home.html"
)


def test_visual_type_scale_and_spacing_tokens() -> None:
    """Shared type/spacing tokens keep hierarchy consistent across screens."""

    css = PLAY_CSS.read_text(encoding="utf-8")

    assert "--text-kicker:" in css
    assert "--text-helper:" in css
    assert "--text-label:" in css
    assert "--text-body:" in css
    assert "--space-section:" in css
    assert "--focus-ring:" in css
    assert "--muted:" in css

    assert re.search(
        r"\.location-kicker\s*\{[^}]*font-size:\s*var\(--text-kicker\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.moment-block h2\s*\{[^}]*font-size:\s*var\(--text-kicker\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.aspiration-side h2\s*\{[^}]*font-size:\s*var\(--text-kicker\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.side-note\s*\{[^}]*font-size:\s*var\(--text-helper\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.drawer-note\s*\{[^}]*font-size:\s*var\(--text-helper\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.meta,\s*\.meta-line\s*\{[^}]*font-size:\s*var\(--text-helper\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.moment-actions\s*\{[^}]*gap:\s*var\(--space-section\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.story-stage\s*\{[^}]*margin:\s*0 0 var\(--space-section\)",
        css,
        re.DOTALL,
    )
    # Story remains unboxed; character/action regions keep restrained chrome.
    assert re.search(
        r"\.story-stage\s*\{[^}]*border:\s*none",
        css,
        re.DOTALL,
    )
    assert "--parchment:" in css
    assert "--gold:" in css
    assert "--jade:" in css


def test_keyboard_focus_and_form_control_treatment() -> None:
    """Links, summaries, and stack-form inputs expose visible focus treatment."""

    css = PLAY_CSS.read_text(encoding="utf-8")

    assert "a:focus-visible" in css
    assert ".side-panel > summary:focus-visible" in css
    assert ".drawer > summary:focus-visible" in css
    assert ".learn-more > summary:focus-visible" in css
    assert ".stack-form input:focus-visible" in css
    assert ".button:focus-visible" in css
    assert "button:focus-visible" in css
    assert re.search(
        r"a:focus-visible\s*\{[^}]*outline:\s*var\(--focus-ring\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.stack-form input:focus-visible\s*\{[^}]*border-color:\s*var\(--gold\)",
        css,
        re.DOTALL,
    )


def test_templates_keep_copy_and_drop_redundant_width_inlines() -> None:
    """Home CTA sizing moves to CSS; play scene copy and routes stay intact."""

    home = HOME_TEMPLATE.read_text(encoding="utf-8")
    play = PLAY_SCENE_TEMPLATE.read_text(encoding="utf-8")
    css = PLAY_CSS.read_text(encoding="utf-8")

    assert 'href="/new"' in home
    assert "New Game" in home
    assert 'style="width: auto;"' not in home
    assert re.search(
        r"\.nav-actions \.btn-primary[^}]*width:\s*auto",
        css,
        re.DOTALL,
    )

    assert "Working Toward" in play
    assert 'method="post" action="/play/{{ scene.save_id }}/action"' in play
    assert 'class="location-kicker"' in play
    assert 'class="story-stage"' in play
    assert 'class="side-note"' in play
    assert 'class="session-note"' in play
    assert 'value="attempt_breakthrough"' in play
    assert 'name="technique_id"' in play
    # Static layout spacing belongs in CSS; dynamic progress width may remain inline.
    assert 'style="margin-top:' not in play
    assert 'style="width: 100%;"' not in play
    assert 'style="width: {{ prog_pct }}%"' in play
    assert re.search(
        r"\.learn-more-body \.btn-primary[^}]*width:\s*100%",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.side-list \.btn-secondary[^}]*width:\s*100%",
        css,
        re.DOTALL,
    )