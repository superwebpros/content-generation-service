#!/bin/bash

# Monitor a training job in real-time
# Usage: ./monitor-job.sh {jobId}

if [ -z "$1" ]; then
  echo "Usage: ./monitor-job.sh {jobId}"
  exit 1
fi

JOB_ID=$1

echo "📊 Monitoring job: $JOB_ID"
echo "Press Ctrl+C to stop"
echo ""

while true; do
  clear
  echo "=================================================="
  echo "Job ID: $JOB_ID"
  echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "=================================================="
  echo ""

  # Get job status
  STATUS=$(curl -s "http://localhost:5000/api/lora/status/$JOB_ID")
  echo "$STATUS" | jq .

  echo ""
  echo "Recent logs:"
  pm2 logs lora-training-worker --lines 10 --nostream 2>&1 | tail -8

  # Check if completed or failed
  JOB_STATUS=$(echo "$STATUS" | jq -r .status)
  if [ "$JOB_STATUS" = "completed" ] || [ "$JOB_STATUS" = "failed" ]; then
    echo ""
    echo "=================================================="
    echo "Job $JOB_STATUS!"
    echo "=================================================="
    break
  fi

  sleep 5
done
