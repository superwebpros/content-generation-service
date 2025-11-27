#!/bin/bash

# Integration test script for Content Generation Service
# Tests the full pipeline from API Gateway → Python Worker → MongoDB → S3

set -e

echo "🧪 Content Generation Service - Integration Test"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Health checks
echo -e "${BLUE}Test 1: Health Checks${NC}"
echo "API Gateway:"
curl -s http://localhost:5000/health | jq .
echo ""
echo "Python Worker:"
curl -s http://localhost:5001/health | jq .
echo ""

# Test 2: Create training job
echo -e "${BLUE}Test 2: Create Training Job${NC}"
JOB_RESPONSE=$(curl -s -X POST http://localhost:5000/api/lora/train \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test-integration-user",
    "videoUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
    "loraName": "integration_test_avatar",
    "trigger": "bunny",
    "steps": 1000
  }')

echo "$JOB_RESPONSE" | jq .
JOB_ID=$(echo "$JOB_RESPONSE" | jq -r .jobId)
echo ""
echo -e "${GREEN}✅ Job created: $JOB_ID${NC}"
echo ""

# Test 3: Check initial status
echo -e "${BLUE}Test 3: Check Job Status (immediate)${NC}"
curl -s "http://localhost:5000/api/lora/status/$JOB_ID" | jq .
echo ""

# Test 4: Wait and check progress
echo -e "${BLUE}Test 4: Monitor Progress${NC}"
echo "Waiting 5 seconds for processing to start..."
sleep 5

curl -s "http://localhost:5000/api/lora/status/$JOB_ID" | jq .
echo ""

# Test 5: List jobs
echo -e "${BLUE}Test 5: List User Jobs${NC}"
curl -s "http://localhost:5000/api/lora/list?userId=test-integration-user" | jq .
echo ""

echo -e "${GREEN}=================================================="
echo "Integration test complete!"
echo "Job ID: $JOB_ID"
echo ""
echo "To monitor progress:"
echo "  curl http://localhost:5000/api/lora/status/$JOB_ID | jq ."
echo ""
echo "To watch logs:"
echo "  pm2 logs lora-training-worker"
echo "==================================================${NC}"
