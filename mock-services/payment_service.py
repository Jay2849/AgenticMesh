from fastapi import FastAPI, BackgroundTasks, HTTPException
import datetime
import json
import os
import sys
import traceback

app = FastAPI(title="payment-service")

memory_leak_list = []

class ConnectionPoolExhaustedError(Exception):
    pass

def log_event(level: str, message: str, route: str = "/", stack_trace: str = ""):
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "service": "payment-service",
        "level": level,
        "message": message,
        "stack_trace": stack_trace,
        "route": route,
        "container_id": os.getenv("HOSTNAME", "payment-service-1")
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

@app.post("/pay")
def pay():
    log_event("INFO", "Payment processed successfully", "/pay")
    return {"paid": True}

@app.post("/crash")
def crash():
    # Simulate DB connection pool exhaustion
    try:
        def process_payment():
            # mock opening connections in a loop without closing them
            connections = []
            for i in range(21):
                if i >= 20:
                    raise ConnectionPoolExhaustedError("max pool size 20 reached")
                connections.append(f"conn_{i}")
        
        process_payment()
    except Exception as e:
        stack_trace = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        log_event("ERROR", f"{type(e).__name__}: {str(e)}", "/crash", stack_trace)
        raise HTTPException(status_code=500, detail="Internal Server Error")

def leak_memory_task():
    global memory_leak_list
    for _ in range(1000000):
        memory_leak_list.append("LEAK" * 100)
    log_event("WARNING", "Memory pressure warning: high heap usage detected", "/crash/memory-leak")

@app.post("/crash/memory-leak")
def crash_memory_leak(background_tasks: BackgroundTasks):
    background_tasks.add_task(leak_memory_task)
    return {"message": "Memory leak initiated"}
