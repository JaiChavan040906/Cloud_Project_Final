#!/bin/bash
set -e

cd /home/ec2-user/app

# Install dependencies
pip install -r requirements.txt

# Seed the database
python -m app.seed

# Run the app with uvicorn
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /var/log/backend/app.log 2>&1 &

echo "Backend started on port 8000"
