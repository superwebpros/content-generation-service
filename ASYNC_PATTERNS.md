# Async Processing Patterns - Client Notification

## The Problem

Training a LoRA takes **5-10 minutes**.
Image generation takes **10-30 seconds**.

**Bad**: Client waits for 10 minutes with open HTTP connection
**Good**: Return immediately, let client check status

## Pattern 1: Polling (What We Have Now) ✅

**How it works:**

```
Client                    Server
  |                         |
  |-- POST /api/lora/train -|
  |                         | Create job, return jobId
  |<---- 201 {jobId} -------|
  |                         |
  | (wait 30 seconds)       | (processing in background)
  |                         |
  |-- GET /status/jobId ----|
  |<---- {status: "processing", progress: 45%} --|
  |                         |
  | (wait 30 seconds)       |
  |                         |
  |-- GET /status/jobId ----|
  |<---- {status: "completed", modelUrl: "..."} --|
```

**Implementation:**

```javascript
// Client-side (frontend or script)
async function trainLora(videoUrl, loraName) {
  // 1. Submit job
  const response = await fetch('/api/lora/train', {
    method: 'POST',
    body: JSON.stringify({ userId, videoUrl, loraName })
  });

  const { jobId } = await response.json();
  console.log('Job created:', jobId);

  // 2. Poll for completion
  return await pollUntilComplete(jobId);
}

async function pollUntilComplete(jobId, interval = 5000) {
  while (true) {
    const response = await fetch(`/api/lora/status/${jobId}`);
    const job = await response.json();

    console.log(`Progress: ${job.progress}%`);

    if (job.status === 'completed') {
      console.log('Complete! Model:', job.modelUrl);
      return job;
    }

    if (job.status === 'failed') {
      throw new Error(job.error);
    }

    // Wait before next check
    await new Promise(resolve => setTimeout(resolve, interval));
  }
}
```

**Pros:**
- ✅ Simple to implement (we already have it!)
- ✅ Works everywhere (no special infrastructure)
- ✅ Client controls polling frequency
- ✅ Stateless server

**Cons:**
- ❌ Wastes HTTP requests
- ❌ Not real-time
- ❌ Client must stay connected

## Pattern 2: Webhooks (Recommended for Production)

**How it works:**

```
Client                    Server
  |                         |
  |-- POST /api/lora/train -|
  |    (with webhookUrl)    | Create job
  |<---- 201 {jobId} -------|
  |                         |
  | (client can disconnect) | (processing...)
  |                         |
  |                         | Job complete!
  |<-- POST to webhookUrl --|
  |    {jobId, status, modelUrl}
```

**Implementation:**

```javascript
// API endpoint accepts webhook URL
router.post('/train', async (req, res) => {
  const { userId, videoUrl, loraName, webhookUrl } = req.body;

  const job = new Job({
    jobId,
    userId,
    config: { loraName, webhookUrl },  // Store webhook URL
    status: 'queued'
  });

  await job.save();
  await triggerTrainingWorker(jobId, {...});

  res.status(201).json({ jobId });
});

// In training pipeline, when complete:
async function notifyWebhook(job) {
  if (job.config.webhookUrl) {
    try {
      await fetch(job.config.webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jobId: job.jobId,
          status: 'completed',
          modelUrl: job.versions[0].modelUrl,
          timestamp: new Date().toISOString()
        })
      });
    } catch (error) {
      console.error('Webhook failed:', error);
      // Don't fail the job if webhook fails
    }
  }
}
```

**Client usage:**

```javascript
// Client provides a webhook endpoint
await fetch('/api/lora/train', {
  method: 'POST',
  body: JSON.stringify({
    userId: 'user123',
    videoUrl: 'https://...',
    loraName: 'my_lora',
    webhookUrl: 'https://your-app.com/api/lora-complete'  // Your callback
  })
});

// Your webhook endpoint receives notification when done
app.post('/api/lora-complete', (req, res) => {
  const { jobId, modelUrl } = req.body;
  console.log('LoRA ready!', modelUrl);

  // Update your UI, send email, etc.
  res.status(200).send('OK');
});
```

**Pros:**
- ✅ No polling waste
- ✅ Instant notification
- ✅ Client can disconnect
- ✅ Server-initiated

**Cons:**
- ❌ Requires client to expose webhook endpoint
- ❌ Webhook must be publicly accessible
- ❌ Need retry logic if webhook fails

## Pattern 3: Server-Sent Events (SSE)

**Real-time updates** - best for browser clients

```javascript
// Endpoint streams updates
router.get('/lora/stream/:jobId', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const { jobId } = req.params;

  // Send updates every second
  const interval = setInterval(async () => {
    const job = await Job.findOne({ jobId });

    res.write(`data: ${JSON.stringify({
      status: job.status,
      progress: job.progress
    })}\n\n`);

    if (job.status === 'completed' || job.status === 'failed') {
      clearInterval(interval);
      res.end();
    }
  }, 1000);

  req.on('close', () => {
    clearInterval(interval);
  });
});
```

**Client (browser):**

```javascript
const eventSource = new EventSource(`/api/lora/stream/${jobId}`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.progress);
  updateProgressBar(data.progress);

  if (data.status === 'completed') {
    console.log('Done!');
    eventSource.close();
  }
};
```

**Pros:**
- ✅ Real-time updates
- ✅ Great for browser UIs
- ✅ Standard web technology
- ✅ Shows live progress

**Cons:**
- ❌ Keeps connection open
- ❌ Doesn't work well for scripts/CLI
- ❌ Limited browser connections (6 per domain)

## Pattern 4: WebSockets

**Bidirectional real-time** - overkill for this use case

Only use if you need two-way communication (client can cancel jobs, etc.)

## Pattern 5: Message Queue + Polling

**Hybrid approach** - scale to high volume

```
Client -> API Gateway -> Job Queue (Redis/BullMQ)
                              |
                         Workers poll queue
                              |
                         Update MongoDB
                              |
                    Client polls MongoDB
```

Better for scaling, but adds complexity.

---

## My Recommendation for You

### Short-term: **Polling + Webhooks (Optional)**

**Why:**
- Polling works now (simple, no changes needed)
- Add webhooks as optional parameter
- Clients choose: poll OR webhook

**Implementation:**

```javascript
// Make webhookUrl optional
POST /api/lora/train
{
  "userId": "...",
  "videoUrl": "...",
  "loraName": "...",
  "webhookUrl": "https://your-app.com/callback"  // OPTIONAL
}

// If webhookUrl provided → notify when done
// If not → client polls /api/lora/status/:jobId
```

**For swp-next UI:**
- Use SSE for real-time progress bars
- User sees live training progress

**For API clients/scripts:**
- Use polling (simple, works everywhere)
- OR provide webhook URL

### Long-term: Message Queue

When you scale to 100+ concurrent jobs, add:
- **BullMQ** (Redis-based queue)
- Worker pool
- Better job management

But not needed yet!

---

## Implementation: Add Webhooks Now

Want me to add webhook support? It's easy:

1. Add `webhookUrl` field to Job schema
2. Call webhook in training pipeline after completion
3. Add retry logic (3 attempts)
4. Document in API

Should take ~10 minutes to implement.

---

## For Testing: Environment-Based Mocking

```javascript
// services/api-gateway/src/config/fal-client.js

import { fal } from '@fal-ai/client';

// In tests, use mock
if (process.env.NODE_ENV === 'test') {
  export const falClient = {
    subscribe: async () => ({
      images: [{ url: 'https://mock.com/image.png', width: 1024, height: 1024 }]
    }),
    storage: {
      upload: async () => 'https://mock.com/uploaded.jpg'
    }
  };
} else {
  // Production: real fal.ai
  fal.config({ credentials: process.env.FAL_KEY });
  export const falClient = fal;
}
```

Then tests are free:
```bash
NODE_ENV=test npm test  # Uses mocks, $0 cost
NODE_ENV=production npm start  # Uses real fal.ai
```

---

## What Would You Like?

1. **Add webhook support** (optional callbacks)
2. **Add SSE endpoint** (for swp-next real-time UI)
3. **Just document polling** (keep it simple)
4. **Add proper test mocks** (avoid API costs in tests)

All of the above?
