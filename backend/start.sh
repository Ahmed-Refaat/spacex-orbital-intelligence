#!/bin/bash
cd /home/clawd/prod/spacex-orbital-intelligence/backend
source venv/bin/activate
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
