import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from esm_fold import app as fastapi_app


def export_openapi(app: FastAPI, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(
            get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                routes=app.routes,
            ),
            f,
        )


if __name__ == "__main__":
    export_openapi(fastapi_app, "openapi.json")
