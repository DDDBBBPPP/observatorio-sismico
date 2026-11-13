from fastapi import FastAPI

from .status import service_status


app = FastAPI(title="Observatorio Sísmico API")


@app.get("/api/salud")
def health() -> dict:
    return {
        "service": "api",
        **service_status("ready"),
        "ingestion": "not_started",
    }
