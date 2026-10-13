from fastapi import FastAPI

app = FastAPI(
    title="Enterprise Integration Hub",
    description="API for enterprise system integrations.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": "integration-service",
    }
