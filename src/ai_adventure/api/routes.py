"""FastAPI routes (thin HTTP adapters)."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ai_adventure.services import GameAppService, HomePageModel

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "presentation" / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


def get_game_app_service(request: Request) -> GameAppService:
    """Resolve the application service from app state (dependency injection)."""

    return request.app.state.game_app_service


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    service: GameAppService = Depends(get_game_app_service),
) -> HTMLResponse:
    """Render the home page from engine outcomes + narrator text."""

    model: HomePageModel = service.build_home_page()
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
