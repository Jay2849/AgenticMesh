from fastapi import FastAPI
import datetime
import json
import os

app = FastAPI(title="ingestion-service")

def log_event(level: str, message: str, route: str = "/", stack_trace: str = ""):
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "service": "ingestion-service",
        "level": level,
        "message": message,
        "stack_trace": stack_trace,
        "route": route,
        "container_id": os.getenv("HOSTNAME", "ingestion-service-1")
    }
    print(json.dumps(log_entry), flush=True)
    try:
        import httpx
        httpx.post("http://ingestion-daemon:8080/ingest", json=log_entry, timeout=1.0)
    except Exception:
        pass

@app.get("/health")
def health():
    return {"status": "OK"}

@app.post("/ingest")
def ingest():
    log_event("INFO", "Data batch ingested successfully", "/ingest")
    return {"ingested": True}
