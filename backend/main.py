from fastapi import FastAPI

app = FastAPI(
    title="ArtMneme API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
