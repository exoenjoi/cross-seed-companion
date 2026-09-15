from fastapi import FastAPI

app = FastAPI(title="Cross-Seed Companion")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
