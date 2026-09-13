#!/bin/bash
uvicorn auth_service:app --host 0.0.0.0 --port 8001 &
uvicorn payment_service:app --host 0.0.0.0 --port 8002 &
uvicorn ingestion_service:app --host 0.0.0.0 --port 8003 &
python traffic_generator.py
