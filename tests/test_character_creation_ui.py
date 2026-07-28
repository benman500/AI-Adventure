"""Presentation checks for character-creation form layout (UI-only)."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import cast

import pytest
from httpx2 import ASGITransport, AsyncClient

from ai_adventure.engine.identity import list_personality_questions
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, make_test_app
from tests.pytest_keyword_utils import strip_retained_keyword_quotes

REPO_ROOT = Path(__file__).resolve().parents[1]
NEW_GAME_TEMPLATE = (
    REPO_ROOT
    / "src"
    / "ai_adventure"
    / "presentation"
    / "templates"
    / "new_game.html"
)
CREATION_CSS = (
    REPO_ROOT / "src" / "ai_adventure" / "presentation" / "static" / "css" / "main.css"
)

EXPECTED_BACKGROUNDS = ("merchant_family", "alchemists_apprentice", "hunter")


def test_strip_retained_keyword_quotes_for_orchestrator_k_flag() -> None:
    """Windows shlex (posix=False) may leave quotes inside pytest ``-k`` values."""

    assert (
        strip_retained_keyword_quotes('"character and creation"')
        == "character and creation"
    )
    assert (
        strip_retained_keyword_quotes("'character and creation'")
        == "character and creation"
    )
    assert strip_retained_keyword_quotes("character and creation") == (
        "character and creation"
    )
    assert strip_retained_keyword_quotes(None) is None


class _FormSnippetParser(HTMLParser):
    """Collect fieldset blocks and named form controls from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.form_attrs: dict[str, str] | None = None
        self.fieldsets: list[dict[str, object]] = []
        self.controls: list[tuple[str, str, str]] = []
        self._fieldset_stack: list[dict[str, object]] = []
        self._capture_legend = False
        self._legend_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: (value or "") for key, value in attrs}
        if tag == "form" and self.form_attrs is None:
            self.form_attrs = attr_map
        if tag == "fieldset":
            block: dict[str, object] = {
                "attrs": attr_map,
                "legend": "",
                "inputs": [],
            }
            self.fieldsets.append(block)
            self._fieldset_stack.append(block)
        if tag == "legend" and self._fieldset_stack:
            self._capture_legend = True
            self._legend_parts = []
        if tag == "input":
            name = attr_map.get("name", "")
            value = attr_map.get("value", "")
            input_type = attr_map.get("type", "text")
            if name:
                self.controls.append((input_type, name, value))
                if self._fieldset_stack:
                    cast(
                        list[tuple[str, str, str]],
                        self._fieldset_stack[-1]["inputs"],
                    ).append((input_type, name, value))

    def handle_endtag(self, tag: str) -> None:
        if tag == "legend" and self._capture_legend and self._fieldset_stack:
            self._fieldset_stack[-1]["legend"] = "".join(self._legend_parts).strip()
            self._capture_legend = False
            self._legend_parts = []
        if tag == "fieldset" and self._fieldset_stack:
            self._fieldset_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._capture_legend:
            self._legend_parts.append(data)


def _parse_new_game_html(html: str) -> _FormSnippetParser:
    parser = _FormSnippetParser()
    parser.feed(html)
    return parser


def test_new_game_template_groups_choices_under_fieldsets() -> None:
    """Template keeps label cards and associates each question with its answers."""

    template = NEW_GAME_TEMPLATE.read_text(encoding="utf-8")
    css = CREATION_CSS.read_text(encoding="utf-8")

    assert 'method="post"' in template
    assert 'action="/new"' in template
    assert 'name="character_name"' in template
    assert 'name="background_id"' in template
    assert 'class="bg-card' in template
    assert "<fieldset" in template
    assert "<legend" in template
    assert 'data-question-id="{{ question.id }}"' in template
    assert 'name="answer_{{ question.id }}"' in template
    assert "{{ answer.id }}" in template
    assert "{{ answer.label }}" in template
    assert 'id="vn-next"' in template
    assert 'id="vn-submit"' in template
    assert "btn-primary" in template
    assert "btn-secondary" in template
    assert "<noscript>" in template
    assert 'role="radiogroup"' in template

    # Answers render inside the same fieldset as the question legend/prompt.
    answer_loop = template.index("{% for answer in question.answers %}")
    question_block = template[
        template.index('data-question-id="{{ question.id }}"') : template.index(
            "{% endfor %}",
            answer_loop,
        )
    ]
    assert "vn-prompt" in question_block
    assert "{{ question.prompt }}" in question_block
    assert "answer-card" in question_block
    assert 'name="answer_{{ question.id }}"' in question_block
    assert question_block.index("{{ question.prompt }}") < question_block.index(
        "{% for answer in question.answers %}"
    )

    assert ".bg-card:hover" in css
    assert ".answer-card:hover" in css
    assert ":has(input:checked)" in css
    assert ":has(input:focus-visible)" in css
    assert "@media (max-width: 560px)" in css
    assert ".vn-fieldset" in css
    assert ".vn-nav .btn-secondary" in css
    assert ".vn-nav .btn-primary" in css

@pytest.mark.asyncio
async def test_new_game_form_contract_and_question_grouping(tmp_path: Path) -> None:
    """Rendered creation form preserves contract and nests answers under questions."""

    app = make_test_app(tmp_path, filename="character_creation_ui.db")
    questions = list_personality_questions()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        response = await client.get("/new")
        assert response.status_code == 200
        html = response.text
        parsed = _parse_new_game_html(html)

        assert parsed.form_attrs is not None
        assert parsed.form_attrs.get("method", "").lower() == "post"
        assert parsed.form_attrs.get("action") == "/new"

        control_names = {name for _, name, _ in parsed.controls}
        assert "character_name" in control_names
        assert "background_id" in control_names
        for question_id in VALID_IDENTITY_ANSWERS:
            assert f"answer_{question_id}" in control_names

        background_values = {
            value
            for input_type, name, value in parsed.controls
            if input_type == "radio" and name == "background_id"
        }
        assert set(EXPECTED_BACKGROUNDS) <= background_values

        for question in questions:
            field_name = f"answer_{question.id}"
            expected_values = {option.id for option in question.answers}
            rendered_values = {
                value
                for input_type, name, value in parsed.controls
                if input_type == "radio" and name == field_name
            }
            assert rendered_values == expected_values

            matching = [
                fieldset
                for fieldset in parsed.fieldsets
                if cast(dict[str, str], fieldset["attrs"]).get("data-question-id")
                == question.id
            ]
            assert len(matching) == 1
            fieldset = matching[0]
            legend = str(fieldset["legend"])
            assert question.prompt in legend
            nested_inputs = cast(list[tuple[str, str, str]], fieldset["inputs"])
            nested_names = {name for _, name, _ in nested_inputs}
            assert nested_names == {field_name}
            nested_values = {value for _, _, value in nested_inputs}
            assert nested_values == expected_values
            # Choices appear after the legend/prompt in document order within this
            # fieldset. Scope + unescape so Jinja autoescape (e.g. elder&#39;s) cannot
            # false-fail a plain-text index against question.prompt.
            fieldset_match = re.search(
                rf'<fieldset[^>]*\bdata-question-id="{re.escape(question.id)}"[^>]*>(.*?)</fieldset>',
                html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            assert fieldset_match is not None
            fieldset_html = unescape(fieldset_match.group(1))
            prompt_idx = fieldset_html.index(question.prompt)
            first_answer_idx = min(
                fieldset_html.index(f'value="{option.id}"', prompt_idx)
                for option in question.answers
            )
            assert prompt_idx < first_answer_idx

        assert re.search(r'class="[^"]*\bbg-card\b', html)
        assert re.search(r'class="[^"]*\banswer-card\b', html)
        assert html.count("<fieldset") >= 2 + len(questions)
        assert html.count("<legend") >= 2 + len(questions)
        assert 'id="vn-next"' in html
        assert 'id="vn-submit"' in html
        assert "btn-primary" in html
        assert "btn-secondary" in html
        assert 'role="radiogroup"' in html
        assert html.count('role="radiogroup"') >= 1 + len(questions)