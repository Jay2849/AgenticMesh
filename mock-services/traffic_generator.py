import asyncio
import httpx
from fastapi import FastAPI, HTTPException
import contextlib
import uvicorn

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(traffic_loop())
    yield
    task.cancel()

app = FastAPI(title="traffic-generator", lifespan=lifespan)

async def traffic_loop():
    async with httpx.AsyncClient() as client:
        while True:
            try:
                await client.get("http://localhost:8001/verify")
                await client.post("http://localhost:8002/pay")
                await client.post("http://localhost:8003/ingest")
            except Exception as e:
                print(f"Traffic loop error: {e}")
            await asyncio.sleep(1)

@app.post("/inject-crash")
async def inject_crash(service: str, type: str = "pool"):
    async with httpx.AsyncClient() as client:
        if service == "payment":
            try:
                if type == "pool":
                    await client.post("http://localhost:8002/crash")
                elif type == "memory":
                    await client.post("http://localhost:8002/crash/memory-leak")
            except Exception as e:
                print(f"Crash injection error: {e}")
            return {"status": "crash injected into payment service"}
        raise HTTPException(status_code=400, detail="Unknown service")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
