#!/bin/bash
set -e

cd /home/ec2-user/app

# Install dependencies with uv
uv sync --frozen --no-dev

# Seed the database
uv run python -m app.seed

# Run the app with uvicorn
nohup uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    > /var/log/backend/app.log 2>&1 &

echo "Backend started on port 8000"
