#!/bin/bash

# Test SSE (Server-Sent Events) streaming for real-time progress
# Usage: ./test-sse-stream.sh {jobId}

if [ -z "$1" ]; then
  echo "Usage: ./test-sse-stream.sh {jobId}"
  echo ""
  echo "Example:"
  echo "  # Create a job first"
  echo "  JOB_ID=\$(curl -s -X POST http://localhost:5000/api/lora/train -d '{...}' | jq -r .jobId)"
  echo "  # Then stream it"
  echo "  ./test-sse-stream.sh \$JOB_ID"
  exit 1
fi

JOB_ID=$1

echo "📡 Connecting to SSE stream for job: $JOB_ID"
echo "Press Ctrl+C to stop"
echo "========================================"
echo ""

# Use curl with no-buffer to stream Server-Sent Events
curl -N -H "Accept: text/event-stream" \
  "http://localhost:5000/api/stream/job/$JOB_ID" | \
  while IFS= read -r line; do
    if [[ $line == data:* ]]; then
      # Extract JSON after "data: "
      json_data="${line#data: }"

      # Pretty print with jq if available
      if command -v jq &> /dev/null; then
        echo "$json_data" | jq -C '.'
      else
        echo "$json_data"
      fi
      echo "---"
    fi
  done
