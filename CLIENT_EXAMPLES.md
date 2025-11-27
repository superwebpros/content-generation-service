# Client Examples - All Async Notification Patterns

## Pattern 1: Polling (Simple, Works Everywhere)

### Node.js/JavaScript

```javascript
async function trainLoraWithPolling(videoUrl, loraName) {
  // 1. Submit job
  const response = await fetch('http://localhost:5000/api/lora/train', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userId: 'user123',
      videoUrl,
      loraName,
      trigger: 'person',
      steps: 2500
    })
  });

  const { jobId } = await response.json();
  console.log('Job created:', jobId);

  // 2. Poll until complete
  while (true) {
    const statusResponse = await fetch(`http://localhost:5000/api/lora/status/${jobId}`);
    const job = await statusResponse.json();

    console.log(`Progress: ${job.progress}% - Status: ${job.status}`);

    if (job.status === 'completed') {
      console.log('✅ Training complete!');
      console.log('Model URL:', job.modelUrl);
      return job;
    }

    if (job.status === 'failed') {
      throw new Error(`Training failed: ${job.error}`);
    }

    // Wait 5 seconds before next check
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}

// Usage
trainLoraWithPolling(
  'https://example.com/video.mp4',
  'my_avatar'
).then(result => {
  console.log('Done!', result.modelUrl);
});
```

### Bash/CLI

```bash
#!/bin/bash

# Submit job
JOB_RESPONSE=$(curl -s -X POST http://localhost:5000/api/lora/train \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "cli-user",
    "videoUrl": "https://example.com/video.mp4",
    "loraName": "my_lora",
    "trigger": "person",
    "steps": 2500
  }')

JOB_ID=$(echo "$JOB_RESPONSE" | jq -r .jobId)
echo "Job created: $JOB_ID"

# Poll until complete
while true; do
  STATUS=$(curl -s "http://localhost:5000/api/lora/status/$JOB_ID")
  CURRENT_STATUS=$(echo "$STATUS" | jq -r .status)
  PROGRESS=$(echo "$STATUS" | jq -r .progress)

  echo "[$CURRENT_STATUS] Progress: $PROGRESS%"

  if [ "$CURRENT_STATUS" = "completed" ]; then
    echo "✅ Complete!"
    echo "$STATUS" | jq -r .modelUrl
    break
  fi

  if [ "$CURRENT_STATUS" = "failed" ]; then
    echo "❌ Failed"
    echo "$STATUS" | jq -r .error
    exit 1
  fi

  sleep 5
done
```

## Pattern 2: Webhooks (Best for Server-to-Server)

### Submit with Webhook URL

```javascript
const response = await fetch('http://localhost:5000/api/lora/train', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    userId: 'user123',
    videoUrl: 'https://example.com/video.mp4',
    loraName: 'my_avatar',
    trigger: 'person',
    steps: 2500,
    webhookUrl: 'https://your-app.com/api/webhooks/lora-complete'  // Your callback
  })
});

const { jobId } = await response.json();
console.log('Job submitted:', jobId);

// Client can now disconnect!
// Your webhook will be called when done
```

### Webhook Endpoint (Express)

```javascript
// In your app (swp-next, etc.)
app.post('/api/webhooks/lora-complete', (req, res) => {
  const payload = req.body;

  console.log('Webhook received:', payload);

  if (payload.event === 'job.completed') {
    console.log('✅ LoRA training complete!');
    console.log('Job ID:', payload.jobId);
    console.log('Model URL:', payload.lora.modelUrl);
    console.log('Trigger:', payload.lora.trigger);

    // Update your database, send email, notify user, etc.
    notifyUser(payload.userId, 'Your LoRA is ready!', payload.lora.modelUrl);
  }

  if (payload.event === 'job.failed') {
    console.log('❌ Job failed:', payload.error);
    notifyUser(payload.userId, 'Training failed', payload.error);
  }

  // Always respond 200 so service knows webhook succeeded
  res.status(200).send('OK');
});
```

### Webhook Payload (Success)

```json
{
  "event": "job.completed",
  "jobId": "uuid-here",
  "userId": "user123",
  "type": "lora-training",
  "status": "completed",
  "completedAt": "2025-11-27T21:00:00.000Z",
  "timestamp": "2025-11-27T21:00:00.000Z",
  "lora": {
    "modelUrl": "https://content-generation-assets.s3.amazonaws.com/loras/.../model.safetensors",
    "version": 1,
    "trigger": "person"
  }
}
```

### Webhook Payload (Failure)

```json
{
  "event": "job.failed",
  "jobId": "uuid-here",
  "userId": "user123",
  "type": "lora-training",
  "status": "failed",
  "error": "Insufficient frames: 5 < 15 required",
  "failedAt": "2025-11-27T21:00:00.000Z",
  "timestamp": "2025-11-27T21:00:00.000Z"
}
```

## Pattern 3: SSE (Best for Browser/Real-time UI)

### Browser Client (React/Next.js)

```javascript
'use client';

import { useState, useEffect } from 'react';

export default function TrainingProgress({ jobId }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('queued');
  const [modelUrl, setModelUrl] = useState(null);

  useEffect(() => {
    // Connect to SSE stream
    const eventSource = new EventSource(
      `http://localhost:5000/api/stream/job/${jobId}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      console.log('SSE update:', data);

      if (data.event === 'connected') {
        console.log('✅ Connected to stream');
      }

      if (data.event === 'progress') {
        setStatus(data.status);
        setProgress(data.progress);
      }

      if (data.event === 'completed') {
        setStatus('completed');
        setProgress(100);
        setModelUrl(data.lora?.modelUrl || data.images?.[0]?.url);
        eventSource.close();
      }

      if (data.event === 'failed') {
        setStatus('failed');
        console.error('Job failed:', data.error);
        eventSource.close();
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
    };

    // Cleanup on unmount
    return () => eventSource.close();
  }, [jobId]);

  return (
    <div>
      <h2>Training Progress</h2>
      <div>Status: {status}</div>
      <div>Progress: {progress}%</div>
      <progress value={progress} max={100} />

      {modelUrl && (
        <div>
          <h3>✅ Complete!</h3>
          <a href={modelUrl}>Download Model</a>
        </div>
      )}
    </div>
  );
}
```

### Vanilla JavaScript

```html
<!DOCTYPE html>
<html>
<head>
  <title>LoRA Training Monitor</title>
</head>
<body>
  <h1>Training Progress</h1>
  <div id="status">Connecting...</div>
  <progress id="progress" value="0" max="100"></progress>
  <div id="result"></div>

  <script>
    const jobId = 'your-job-id';
    const eventSource = new EventSource(`/api/stream/job/${jobId}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      document.getElementById('status').textContent =
        `Status: ${data.status} - Progress: ${data.progress}%`;

      document.getElementById('progress').value = data.progress;

      if (data.event === 'completed') {
        document.getElementById('result').innerHTML =
          `<h2>✅ Complete!</h2><a href="${data.lora.modelUrl}">Download Model</a>`;
        eventSource.close();
      }

      if (data.event === 'failed') {
        document.getElementById('result').innerHTML =
          `<h2>❌ Failed</h2><p>${data.error}</p>`;
        eventSource.close();
      }
    };

    eventSource.onerror = (error) => {
      console.error('Connection error:', error);
      document.getElementById('status').textContent = 'Connection lost';
    };
  </script>
</body>
</html>
```

### Node.js SSE Client

```javascript
import EventSource from 'eventsource';

function monitorJob(jobId) {
  return new Promise((resolve, reject) => {
    const url = `http://localhost:5000/api/stream/job/${jobId}`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      console.log(`[${data.status}] ${data.progress}%`);

      if (data.event === 'completed') {
        eventSource.close();
        resolve(data);
      }

      if (data.event === 'failed') {
        eventSource.close();
        reject(new Error(data.error));
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
      reject(error);
    };
  });
}

// Usage
const result = await monitorJob('job-id-here');
console.log('Done!', result.lora.modelUrl);
```

## Pattern Comparison

| Pattern | Best For | Pros | Cons |
|---------|----------|------|------|
| **Polling** | CLI tools, scripts | Simple, works everywhere | Wastes requests, not real-time |
| **Webhooks** | Server-to-server | Instant notification, no polling | Requires public endpoint |
| **SSE** | Browser UIs | Real-time, great UX | Keeps connection open |

## Choosing the Right Pattern

### Use Polling When:
- Client is a CLI tool or script
- Simplicity is priority
- No real-time UI needed

### Use Webhooks When:
- Server-to-server integration
- Client has public API endpoint
- Want instant notification without polling

### Use SSE When:
- Building browser UI (swp-next)
- Want real-time progress bars
- User is actively watching

## Combined Example (Best of All)

```javascript
async function trainWithMultipleNotifications(videoUrl, loraName) {
  // Submit with optional webhook
  const response = await fetch('/api/lora/train', {
    method: 'POST',
    body: JSON.stringify({
      userId: 'user123',
      videoUrl,
      loraName,
      webhookUrl: 'https://my-app.com/webhook', // Optional
    })
  });

  const { jobId } = await response.json();

  // Option 1: Poll (fallback)
  // pollUntilComplete(jobId);

  // Option 2: SSE (real-time UI)
  // const eventSource = new EventSource(`/api/stream/job/${jobId}`);

  // Option 3: Just wait for webhook
  // (webhook will notify when done)

  return jobId;
}
```

## Testing All Patterns

```bash
# Test polling
./monitor-job.sh {jobId}

# Test SSE
./test-sse-stream.sh {jobId}

# Test webhooks (need a webhook receiver)
# Use webhook.site for testing:
WEBHOOK_URL="https://webhook.site/your-unique-url"

curl -X POST http://localhost:5000/api/lora/train \
  -H "Content-Type: application/json" \
  -d "{
    \"userId\": \"test\",
    \"videoUrl\": \"https://example.com/video.mp4\",
    \"loraName\": \"test\",
    \"webhookUrl\": \"$WEBHOOK_URL\"
  }"

# Then check webhook.site to see the notification!
```

## Mock Testing (Avoid API Costs)

### Run Tests Without Real APIs

```bash
# Node.js tests (uses mocks in tests/__mocks__/@fal-ai/client.js)
cd services/api-gateway
npm test  # Costs $0

# Python tests (uses mocks in tests/conftest.py)
cd services/lora-training
source venv/bin/activate
pytest  # Costs $0
```

### Run Real API Tests (Manual Only)

```bash
# Only when you really need to verify against real APIs
REAL_API_TESTS=true pytest tests/test_training_with_mocks.py::test_real_training_with_fal_ai

# This will cost $6 (one real LoRA training)
# Use sparingly!
```

## Example: swp-next Integration

### In swp-next (your user-facing app)

```typescript
// app/training/[jobId]/page.tsx
'use client';

import { useEffect, useState } from 'react';

export default function TrainingPage({ params }: { params: { jobId: string } }) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('connecting');

  useEffect(() => {
    const eventSource = new EventSource(
      `https://content.superwebpros.com/api/stream/job/${params.jobId}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      setStatus(data.status);
      setProgress(data.progress);

      if (data.event === 'completed') {
        // Show success, allow download
        eventSource.close();
      }
    };

    return () => eventSource.close();
  }, [params.jobId]);

  return (
    <div>
      <h1>Training Your LoRA</h1>
      <p>Status: {status}</p>
      <ProgressBar value={progress} />
    </div>
  );
}
```

## Cost Control

**All test suites use mocks by default** = $0 cost

Only manual/production runs use real APIs:
- Development: Use mocks
- CI/CD: Use mocks
- Production: Real APIs
- Manual testing: Set `REAL_API_TESTS=true`
