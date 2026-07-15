"""ASGI entrypoint and CLI runner."""

import uvicorn

from ai_adventure.api import create_app

app = create_app()


def run() -> None:
    """Run the development server."""

    uvicorn.run("ai_adventure.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
