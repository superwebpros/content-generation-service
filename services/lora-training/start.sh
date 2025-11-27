#!/bin/bash
cd /var/www/content-generation-service/services/lora-training
source venv/bin/activate
exec uvicorn app:app --host 0.0.0.0 --port 5001
