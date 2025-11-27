# Transcription Service - Usage Examples

## Overview

The transcription service uses **AssemblyAI** to transcribe audio/video files. Files are stored in S3, transcripts are saved as both JSON (full data) and TXT (just text).

## Basic Usage

### 1. Transcribe from Public URL

```bash
curl -X POST http://localhost:5000/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user123",
    "audioUrl": "https://example.com/podcast.mp3",
    "fileName": "episode-01.mp3"
  }'
```

Response:
```json
{
  "jobId": "uuid-here",
  "status": "processing",
  "message": "Transcription started"
}
```

### 2. Transcribe from S3

```bash
curl -X POST http://localhost:5000/api/transcribe/from-s3 \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user123",
    "s3Url": "https://content-generation-assets.s3.amazonaws.com/audio/my-file.mp3"
  }'
```

### 3. Transcribe with Options

```bash
curl -X POST http://localhost:5000/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user123",
    "audioUrl": "https://example.com/interview.mp3",
    "options": {
      "speaker_labels": true,
      "auto_chapters": true,
      "sentiment_analysis": true,
      "entity_detection": true
    }
  }'
```

### 4. Transcribe with Webhook Notification

```bash
curl -X POST http://localhost:5000/api/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user123",
    "audioUrl": "https://example.com/meeting.mp4",
    "webhookUrl": "https://your-app.com/api/transcription-complete"
  }'
```

## Checking Results

### Polling (Simple)

```javascript
async function waitForTranscription(jobId) {
  while (true) {
    const response = await fetch(`http://localhost:5000/api/jobs/${jobId}`);
    const job = await response.json();

    console.log(`Progress: ${job.progress}%`);

    if (job.status === 'completed') {
      const transcript = job.versions[0];
      console.log('Transcript URL:', transcript.textUrl);
      console.log('Word count:', transcript.wordCount);
      console.log('Duration:', transcript.duration, 'seconds');

      // Download the text
      const textResponse = await fetch(transcript.textUrl);
      const text = await textResponse.text();
      console.log('Transcript:', text);

      return text;
    }

    if (job.status === 'failed') {
      throw new Error(job.error);
    }

    await new Promise(r => setTimeout(r, 3000)); // Check every 3 seconds
  }
}
```

### SSE (Real-time)

```javascript
function watchTranscription(jobId) {
  const eventSource = new EventSource(`/api/stream/job/${jobId}`);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.event === 'progress') {
      console.log(`Progress: ${data.progress}%`);
      updateProgressBar(data.progress);
    }

    if (data.event === 'completed') {
      console.log('✅ Transcription ready!');
      console.log('Text URL:', data.transcription.textUrl);
      eventSource.close();
    }
  };
}
```

### Webhook (Automatic Notification)

```javascript
// In your app (receives webhook)
app.post('/api/transcription-complete', (req, res) => {
  const payload = req.body;

  if (payload.event === 'job.completed') {
    console.log('✅ Transcription complete!');
    console.log('Job ID:', payload.jobId);
    console.log('Text URL:', payload.transcription.textUrl);
    console.log('Word count:', payload.transcription.wordCount);
    console.log('Duration:', payload.transcription.duration);

    // Download transcript text
    fetch(payload.transcription.textUrl)
      .then(r => r.text())
      .then(text => {
        console.log('Transcript:', text);
        // Store in your database, display to user, etc.
      });
  }

  res.status(200).send('OK');
});
```

## Storage Structure

Transcripts are stored in S3:

```
content-generation-assets/
└── transcripts/
    └── {userId}/
        └── {jobId}/
            ├── transcript.json   # Full AssemblyAI response
            └── transcript.txt    # Just the text
```

## AssemblyAI Features

Enable advanced features via `options`:

```javascript
{
  "options": {
    // Speaker identification
    "speaker_labels": true,

    // Auto-generate chapters
    "auto_chapters": true,

    // Sentiment analysis
    "sentiment_analysis": true,

    // Entity detection (names, places, etc.)
    "entity_detection": true,

    // Content moderation
    "content_safety": true,

    // PII redaction
    "redact_pii": true,
    "redact_pii_policies": ["person_name", "email_address"],

    // Language detection
    "language_detection": true,

    // Custom vocabulary
    "word_boost": ["SuperWebPros", "LoRA", "fal.ai"],

    // Formatting
    "punctuate": true,
    "format_text": true
  }
}
```

## Cost

AssemblyAI pricing (as of 2024):
- **Core transcription**: $0.00025/second (~$0.015/minute, $0.90/hour)
- **Speaker labels**: +$0.01/minute
- **Sentiment**: +$0.005/minute
- **Most features**: Included in base price

Example costs:
- 5 min podcast: $0.075 (7.5 cents)
- 30 min interview: $0.45
- 1 hour meeting: $0.90

Much cheaper than manual transcription!

## Example: Podcast Transcription Workflow

```javascript
async function transcribePodcast(audioUrl, episodeName) {
  // 1. Start transcription
  const response = await fetch('/api/transcribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userId: 'podcast-team',
      audioUrl,
      fileName: episodeName,
      options: {
        speaker_labels: true,
        auto_chapters: true,
        word_boost: ['SuperWebPros', 'Jesse', 'SEO']
      },
      webhookUrl: 'https://your-cms.com/api/podcast-transcribed'
    })
  });

  const { jobId } = await response.json();

  // 2. Your webhook receives notification when done
  // 3. Download transcript and add to CMS
  // 4. Generate blog post from transcript
  // 5. Create social media clips from chapters

  return jobId;
}
```

## Testing

Transcription tested successfully:
- ✅ Submitted to AssemblyAI (10 second audio)
- ✅ Transcript completed
- ✅ Uploaded to S3 (JSON + TXT)
- ✅ MongoDB updated with results
- ✅ Total time: ~10 seconds

Test job: `6b8a6895-c2f4-40c4-9924-418a62b7c53f`

## Common Use Cases

1. **Podcast transcription** - Auto-transcribe episodes for SEO/blog posts
2. **Meeting notes** - Transcribe Zoom/Teams recordings
3. **Video captions** - Generate subtitles for YouTube videos
4. **Content repurposing** - Turn audio into written content
5. **Search/indexing** - Make audio searchable

## S3 URLs

After transcription completes:
- Full JSON: `https://content-generation-assets.s3.amazonaws.com/transcripts/{userId}/{jobId}/transcript.json`
- Plain text: `https://content-generation-assets.s3.amazonaws.com/transcripts/{userId}/{jobId}/transcript.txt`

## API Endpoints

- `POST /api/transcribe` - Transcribe from any URL
- `POST /api/transcribe/from-s3` - Transcribe from S3
- `GET /api/jobs/:jobId` - Get transcription status
- `GET /api/stream/job/:jobId` - Stream real-time progress

## Next Steps

Integration ideas:
- Auto-transcribe all video uploads
- Generate blog posts from podcasts
- Create searchable audio library
- Add to your content generation workflows
