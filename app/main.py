from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.prowlarr import ProwlarrClient
from app.routers import actions as actions_router
from app.routers import logs as logs_router
from app.routers import sync as sync_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.prowlarr_client = ProwlarrClient(settings.prowlarr_url, settings.prowlarr_api_key)
    yield
    app.state.prowlarr_client.close()


app = FastAPI(title="Cross-Seed Companion", lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)
app.include_router(sync_router.router)
app.include_router(actions_router.router)
app.include_router(logs_router.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
