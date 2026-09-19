import os
from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
# Baked into the image at build time (Dockerfile ARG APP_VERSION); "dev" when running from source.
templates.env.globals["app_version"] = lambda: os.environ.get("APP_VERSION", "dev")
