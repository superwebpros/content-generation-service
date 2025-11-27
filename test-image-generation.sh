#!/bin/bash

# Test image generation service
# Simple text-based image edit (no file uploads needed for first test)

set -e

echo "🎨 Testing Image Generation Service"
echo "===================================="
echo ""

# Test 1: List available models
echo "Test 1: List Available Models"
echo "------------------------------"
curl -s http://localhost:5000/api/images/models | jq '{total, models: (.models[] | {name, category, cost: .costPerImage})}'
echo ""

# Test 2: Estimate cost
echo "Test 2: Estimate Cost"
echo "---------------------"
curl -s -X POST http://localhost:5000/api/images/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-pro",
    "options": {
      "num_images": 2
    }
  }' | jq .
echo ""

# Test 3: Simple text-to-image generation
echo "Test 3: Generate Image with FLUX Pro"
echo "-------------------------------------"
echo "Generating a simple test image..."

RESPONSE=$(curl -s -X POST http://localhost:5000/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-pro",
    "inputs": {
      "prompt": "A professional headshot of a business consultant in a modern office, studio lighting, corporate photography"
    },
    "options": {
      "num_images": 1
    },
    "userId": "test-image-user"
  }')

echo "$RESPONSE" | jq .

JOB_ID=$(echo "$RESPONSE" | jq -r .jobId)

if [ "$JOB_ID" != "null" ]; then
  echo ""
  echo "✅ Image generated!"
  echo "Job ID: $JOB_ID"
  echo ""
  echo "Image URL:"
  echo "$RESPONSE" | jq -r '.images[0].url'
fi

echo ""
echo "===================================="
echo "Test complete!"
echo "===================================="
