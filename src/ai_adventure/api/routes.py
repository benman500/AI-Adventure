"""FastAPI routes (thin HTTP adapters)."""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ai_adventure.engine import EngineValidationError
from ai_adventure.engine.constants import ACTIVE_SAVE_COOKIE, DELETE_CONFIRMATION_VALUE
from ai_adventure.services import GameAppService

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "presentation" / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


def get_game_app_service(request: Request) -> GameAppService:
    """Resolve the application service from app state (dependency injection)."""

    return request.app.state.game_app_service


def _set_active_save_cookie(response: Response, save_id: str) -> None:
    """Remember the active save for this browser."""

    response.set_cookie(ACTIVE_SAVE_COOKIE, save_id, httponly=True, samesite="lax")


def _identity_answers_from_form(form: object) -> dict[str, str]:
    """Extract answer_<question_id> fields from a Starlette form body."""

    answers: dict[str, str] = {}
    for key, value in form.multi_items():  # type: ignore[attr-defined]
        if key.startswith("answer_") and isinstance(value, str):
            answers[key.removeprefix("answer_")] = value
    return answers


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    service: GameAppService = Depends(get_game_app_service),
) -> HTMLResponse:
    """Title screen linking to saves and new game."""

    model = service.build_home_page()
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "app_name": model.app_name,
            "outcome_summary": model.outcome.summary,
            "outcome_kind": model.outcome.kind.value,
            "narration": model.narration.text,
            "schema_marker": model.schema_marker,
            "authoritative": model.outcome.facts.get("authoritative"),
        },
    )


@router.get("/saves", response_class=HTMLResponse)
def save_list(
    request: Request,
    service: GameAppService = Depends(get_game_app_service),
) -> HTMLResponse:
    """Render the save-list screen."""

    saves = service.list_saves()
    return templates.TemplateResponse(
        request,
        "saves.html",
        {
            "app_name": request.app.state.settings.app_name,
            "saves": saves,
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_game_form(
    request: Request,
    service: GameAppService = Depends(get_game_app_service),
) -> HTMLResponse:
    """Render character creation."""

    form = service.build_new_game_form()
    return templates.TemplateResponse(
        request,
        "new_game.html",
        {
            "app_name": form.app_name,
            "backgrounds": form.backgrounds,
            "questions": form.questions,
            "error": form.error,
            "character_name": "",
            "selected_background": "",
            "answers": {},
        },
    )


@router.post("/new", response_class=HTMLResponse)
async def new_game_submit(
    request: Request,
    character_name: str = Form(...),
    background_id: str = Form(...),
    service: GameAppService = Depends(get_game_app_service),
) -> Response:
    """Create a new game from form data."""

    form = await request.form()
    identity_answers = _identity_answers_from_form(form)

    try:
        loaded = service.create_new_game(
            character_name=character_name,
            background_id=background_id,
            identity_answers=identity_answers,
        )
    except EngineValidationError as exc:
        form_model = service.build_new_game_form(error=exc.message)
        return templates.TemplateResponse(
            request,
            "new_game.html",
            {
                "app_name": form_model.app_name,
                "backgrounds": form_model.backgrounds,
                "questions": form_model.questions,
                "error": form_model.error,
                "character_name": character_name,
                "selected_background": background_id,
                "answers": identity_answers,
            },
            status_code=400,
        )

    response = RedirectResponse(url=f"/play/{loaded.save_id}", status_code=303)
    _set_active_save_cookie(response, loaded.save_id)
    return response


@router.post("/saves/{save_id}/load")
def load_save_route(
    save_id: str,
    service: GameAppService = Depends(get_game_app_service),
) -> Response:
    """Load a save and set it active."""

    try:
        loaded = service.load_save(save_id)
    except EngineValidationError:
        return RedirectResponse(url="/saves", status_code=303)
    response = RedirectResponse(url=f"/play/{loaded.save_id}", status_code=303)
    _set_active_save_cookie(response, loaded.save_id)
    return response


@router.get("/play/{save_id}", response_class=HTMLResponse)
def play_status(
    request: Request,
    save_id: str,
    service: GameAppService = Depends(get_game_app_service),
) -> Response:
    """Minimal loaded-save status (no gameplay systems)."""

    try:
        loaded = service.load_save(save_id)
    except EngineValidationError:
        return RedirectResponse(url="/saves", status_code=303)
    return templates.TemplateResponse(
        request,
        "play_status.html",
        {
            "app_name": loaded.app_name,
            "save": loaded,
        },
    )


@router.get("/saves/{save_id}/delete", response_class=HTMLResponse)
def delete_confirm(
    request: Request,
    save_id: str,
    service: GameAppService = Depends(get_game_app_service),
) -> Response:
    """Show explicit delete confirmation."""

    try:
        model = service.get_delete_confirm(save_id)
    except EngineValidationError:
        return RedirectResponse(url="/saves", status_code=303)
    return templates.TemplateResponse(
        request,
        "confirm_delete.html",
        {
            "app_name": model.app_name,
            "save_id": model.save_id,
            "character_name": model.character_name,
            "error": model.error,
            "confirmation_value": DELETE_CONFIRMATION_VALUE,
        },
    )


@router.post("/saves/{save_id}/delete")
def delete_save_route(
    request: Request,
    save_id: str,
    confirmation: str = Form(...),
    service: GameAppService = Depends(get_game_app_service),
) -> Response:
    """Soft-delete after explicit confirmation."""

    try:
        service.delete_save(save_id, confirmation=confirmation)
    except EngineValidationError as exc:
        try:
            model = service.get_delete_confirm(save_id, error=exc.message)
        except EngineValidationError:
            return RedirectResponse(url="/saves", status_code=303)
        return templates.TemplateResponse(
            request,
            "confirm_delete.html",
            {
                "app_name": model.app_name,
                "save_id": model.save_id,
                "character_name": model.character_name,
                "error": model.error,
                "confirmation_value": DELETE_CONFIRMATION_VALUE,
            },
            status_code=400,
        )
    return RedirectResponse(url="/saves", status_code=303)


@router.get("/api/health")
def health(service: GameAppService = Depends(get_game_app_service)) -> dict[str, object]:
    """JSON health check using the same service/engine path (no AI authority)."""

    model = service.build_home_page()
    return {
        "status": "ok",
        "outcome_kind": model.outcome.kind.value,
        "narration": model.narration.text,
        "schema_marker": model.schema_marker,
    }
