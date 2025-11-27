# Service Boundaries - Next.js App vs Content Generation Service

## The Decision Framework

### Put in **content-generation-service** when:

✅ **Compute-intensive AI/ML operations**
- LoRA training (6+ minute processing)
- Image generation (10-30 second processing)
- Video processing (heavy CPU/GPU)
- Large-scale transcription batches

✅ **Language-specific requirements**
- Python libraries (OpenCV, ML models)
- Specialized SDKs (fal.ai Python client)

✅ **Long-running background jobs**
- Anything > 30 seconds
- Jobs that need progress tracking
- Async processing with webhooks

✅ **Reusable across multiple apps**
- Multiple frontends might use it
- API-first design
- Can be called by scripts, CLI, other services

✅ **Independent scaling needs**
- Might need separate server/resources
- Resource-intensive (might need GPU)
- Different traffic patterns than web app

### Put in **swp-next (Next.js)** when:

✅ **User-facing UI/UX logic**
- Forms, dashboards, visualizations
- Authentication/authorization
- User session management
- Page routing and navigation

✅ **Database CRUD for user data**
- User profiles, preferences
- Settings, subscriptions
- Simple data retrieval/storage

✅ **Fast, synchronous operations**
- < 5 second response time
- No heavy computation
- Simple API calls and aggregation

✅ **Presentation layer**
- Formatting data for display
- Charts, graphs, reports
- UI state management

✅ **Business logic tied to UI**
- Form validation
- User workflows
- Navigation flows

## Analyzing Your Tools

Based on your Baserow data, here's where each tool should live:

### 1. Content Planner ✅ Next.js App

**Why:**
- UI-heavy (dashboards, calendars, visualizations)
- Fast queries (content gaps, ratings)
- User interaction focused
- Data presentation layer

**Architecture:**
```
swp-next (Next.js)
├── /tools/content-planner
│   ├── UI components (calendars, ratings, badges)
│   ├── API routes for data fetching
│   └── Client-side state management
│
└── Calls external services:
    ├── conversation-service (for content analysis)
    └── content-generation-service (for suggestions)
```

**Complexity**: High (but UI complexity, not compute)

---

### 2. SEO Health Checker ✅ Next.js App

**Why:**
- Diagnostic tool (query existing data)
- Fast results (schema validation, technical checks)
- Report generation (UI-focused)
- Interactive dashboard

**Architecture:**
```
swp-next (Next.js)
├── /tools/seo-health-checker
│   ├── Page analyzer UI
│   ├── Schema validator
│   └── Results dashboard
│
└── Might call:
    └── crawl4ai service (for deep site analysis)
```

**Complexity**: Medium (mostly data aggregation)

---

### 3. Customer Journey Analyzer ✅ Next.js App (mostly)

**Why:**
- Analytics/reporting interface
- User flow visualization
- Interactive heat maps/flow diagrams

**But might use content-generation-service for:**
- Video recording analysis (if analyzing session recordings)
- AI-powered insights generation

**Architecture:**
```
swp-next (Next.js)
├── /tools/journey-analyzer
│   ├── Flow visualization UI
│   ├── Analytics dashboard
│   └── Drop-off identification
│
└── Calls:
    └── content-generation-service (if analyzing recordings/multimedia)
```

**Complexity**: High (but mostly data viz complexity)

---

### 4. Content Multiplier ⚡ **HYBRID** (Both!)

**Why:**
- Heavy AI processing → content-generation-service
- UI for managing → swp-next

**This is your **perfect candidate** for service split!**

**Architecture:**
```
swp-next (Next.js) - Frontend
├── /tools/content-multiplier
│   ├── Upload blog post
│   ├── Select output formats
│   ├── Preview/download results
│   └── Progress tracking UI
│
└── Calls ↓

content-generation-service - Backend
├── POST /api/content/multiply
│   ├── Input: Blog post text/URL
│   ├── Generate: Social images, video clips, audio
│   ├── Uses: Image gen, LoRA, transcription services
│   └── Returns: All generated assets
```

**What belongs where:**

**In content-generation-service:**
- Blog → Social images (fal.ai image gen)
- Blog → Short video clips (future video service)
- Blog → Audio narration (TTS service)
- Heavy processing, async jobs

**In swp-next:**
- Upload interface
- Format selection UI
- Progress monitoring (SSE)
- Asset preview/download
- User preferences

---

### 5. Smart Site Analytics ✅ Next.js App

**Why:**
- Pure analytics/reporting
- Query conversation data
- Dashboard/visualization
- Real-time metrics

**Architecture:**
```
swp-next (Next.js)
├── /tools/analytics
│   ├── Conversation metrics dashboard
│   ├── Knowledge gap reports
│   └── Performance charts
│
└── Calls:
    └── conversation-service (existing)
```

**Complexity**: Medium (data aggregation + viz)

---

## The Pattern

### Next.js App (swp-next)
**Role**: User-facing application layer

```typescript
// Example: Content Multiplier UI
'use client';

export default function ContentMultiplier() {
  const [blogUrl, setBlogUrl] = useState('');
  const [jobId, setJobId] = useState(null);

  async function handleSubmit() {
    // Call content-generation-service
    const response = await fetch('https://content.superwebpros.com/api/content/multiply', {
      method: 'POST',
      body: JSON.stringify({
        userId: session.user.id,
        blogUrl,
        outputs: ['social-images', 'video-clips', 'audio']
      })
    });

    const { jobId } = await response.json();
    setJobId(jobId);
  }

  return (
    <div>
      <input value={blogUrl} onChange={e => setBlogUrl(e.target.value)} />
      <button onClick={handleSubmit}>Generate Content</button>

      {jobId && <ProgressMonitor jobId={jobId} />}
    </div>
  );
}
```

### Content Generation Service
**Role**: Heavy lifting, AI processing, background jobs

```javascript
// API endpoint in content-generation-service
router.post('/content/multiply', async (req, res) => {
  const { userId, blogUrl, outputs } = req.body;

  const jobs = [];

  if (outputs.includes('social-images')) {
    // Generate 5 social images with different styles
    jobs.push(generateSocialImages(blogUrl, userId));
  }

  if (outputs.includes('video-clips')) {
    // Generate short video clips
    jobs.push(generateVideoClips(blogUrl, userId));
  }

  // Process in background
  const jobId = uuidv4();
  processMultipleGenerations(jobId, jobs);

  res.json({ jobId });
});
```

---

## Decision Tree

```
New Tool Idea
    ├─ Needs heavy AI/ML processing?
    │  ├─ YES → content-generation-service
    │  └─ NO → Continue ↓
    │
    ├─ Takes > 30 seconds?
    │  ├─ YES → content-generation-service
    │  └─ NO → Continue ↓
    │
    ├─ Needs Python/specialized libs?
    │  ├─ YES → content-generation-service
    │  └─ NO → Continue ↓
    │
    ├─ Reusable across apps?
    │  ├─ YES → content-generation-service
    │  └─ NO → Continue ↓
    │
    └─ Primarily UI/data presentation?
       ├─ YES → swp-next
       └─ HYBRID → Both!
```

---

## Specific Recommendations for Your Tools

### Tools for swp-next (Next.js)

1. **Content Planner** - UI-heavy, fast queries
2. **SEO Health Checker** - Diagnostic reports, interactive
3. **Customer Journey Analyzer** - Data viz, analytics
4. **Smart Site Analytics** - Dashboards, metrics

### Tools for content-generation-service

1. **Content Multiplier** (backend) - Heavy AI processing
   - New endpoint: `POST /api/content/multiply`
   - Orchestrates: image gen, video gen, TTS
   - Returns: jobId, client monitors via SSE/webhook

### Hybrid Tools (Both)

**Content Multiplier**:
- **swp-next**: Upload UI, format selection, preview
- **content-generation-service**: Actual generation

---

## Real-World Examples

### Example 1: SEO Health Checker

**Next.js App (swp-next):**
```typescript
// app/tools/seo-health-checker/page.tsx
'use client';

export default function SEOHealthChecker() {
  const [url, setUrl] = useState('');
  const [results, setResults] = useState(null);

  async function checkSite() {
    // Crawl site (use your crawl4ai service)
    const crawlResponse = await fetch('https://crawl.superwebpros.com/api/crawl', {
      method: 'POST',
      body: JSON.stringify({ url })
    });

    const pages = await crawlResponse.json();

    // Analyze in Next.js (fast, synchronous)
    const issues = analyzeSEOIssues(pages); // Client-side or API route

    setResults(issues);
  }

  return (
    <div>
      <input value={url} onChange={e => setUrl(e.target.value)} />
      <button onClick={checkSite}>Check SEO Health</button>
      {results && <IssuesDashboard issues={results} />}
    </div>
  );
}
```

**Why not a service?**
- Fast processing (< 5 seconds)
- Mostly data aggregation
- Heavy on UI/visualization
- Not reused outside this app

---

### Example 2: Content Multiplier (Hybrid)

**Next.js App (swp-next):**
```typescript
// app/tools/content-multiplier/page.tsx
'use client';

export default function ContentMultiplier() {
  const [jobId, setJobId] = useState(null);

  async function multiply(blogUrl) {
    // Call content-generation-service
    const response = await fetch('https://content.superwebpros.com/api/content/multiply', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${session.token}` },
      body: JSON.stringify({
        userId: session.user.id,
        sourceUrl: blogUrl,
        outputs: {
          socialImages: 5,
          videoClips: 3,
          audioNarration: true
        }
      })
    });

    const { jobId } = await response.json();
    setJobId(jobId);
  }

  return (
    <div>
      <BlogUrlInput onSubmit={multiply} />
      {jobId && (
        <div>
          <LiveProgress jobId={jobId} />  {/* Uses SSE */}
          <AssetGallery jobId={jobId} />
        </div>
      )}
    </div>
  );
}
```

**Content Generation Service:**
```javascript
// services/api-gateway/src/routes/content.js

router.post('/multiply', async (req, res) => {
  const { userId, sourceUrl, outputs } = req.body;

  const jobId = uuidv4();

  // Create orchestration job
  const job = new Job({
    jobId,
    userId,
    type: 'content-multiplication',
    config: { sourceUrl, outputs }
  });

  await job.save();

  // Process in background
  multiplyContent(jobId, sourceUrl, outputs, userId);

  res.json({ jobId });
});

async function multiplyContent(jobId, sourceUrl, outputs, userId) {
  // 1. Fetch blog content
  const blogText = await fetchBlogContent(sourceUrl);

  // 2. Generate social images
  const imageJobs = [];
  for (let i = 0; i < outputs.socialImages; i++) {
    const prompt = generateSocialPrompt(blogText, i);
    imageJobs.push(
      fetch('http://localhost:5000/api/images/generate', {
        method: 'POST',
        body: JSON.stringify({
          model: 'flux-pro',
          inputs: { prompt },
          userId
        })
      })
    );
  }

  // 3. Generate video clips (future)
  // 4. Generate audio narration (future)

  await Promise.all(imageJobs);

  // Update parent job as complete
  await Job.updateOne({ jobId }, { $set: { status: 'completed' } });
}
```

**Why hybrid?**
- UI/UX belongs in Next.js
- Heavy processing belongs in service
- Clean separation of concerns

---

## General Principles

### Next.js App (swp-next) = "The Restaurant Front"
- Customer-facing
- Menu (tools list)
- Takes orders (user input)
- Presents results beautifully
- Fast, responsive UI

### Content Generation Service = "The Kitchen"
- Heavy lifting happens here
- Specialized equipment (AI models)
- Processes orders (background jobs)
- Delivers finished products
- Can serve multiple restaurants (apps)

---

## For Your Specific Tools

| Tool | Location | Reason |
|------|----------|--------|
| **Content Planner** | swp-next | UI-heavy, analytics, fast queries |
| **SEO Health Checker** | swp-next | Diagnostic, reporting, interactive |
| **Journey Analyzer** | swp-next | Data viz, analytics dashboard |
| **Content Multiplier** | **BOTH** | UI in Next.js, processing in service |
| **Smart Site Analytics** | swp-next | Analytics dashboard, conversation data |

---

## When to Add to content-generation-service

**Add new endpoints when you need:**

1. **Content Multiplier** (future)
   ```
   POST /api/content/multiply
   - Input: Blog URL or text
   - Output: Multiple content formats
   - Uses: Image gen, video gen, TTS
   ```

2. **Video Generation** (future)
   ```
   POST /api/video/generate
   - Input: Script + LoRA
   - Output: Talking head video
   - Heavy processing
   ```

3. **Batch Operations** (future)
   ```
   POST /api/batch/process
   - Input: Array of jobs
   - Output: Batch job ID
   - Process 10+ items at once
   ```

4. **Advanced Image Editing** (future)
   ```
   POST /api/images/edit-advanced
   - Input: Complex editing pipeline
   - Output: Processed image
   - Multi-step processing
   ```

---

## Integration Pattern

### swp-next → content-generation-service

```typescript
// In swp-next
export async function generateContentMultiples(blogUrl: string) {
  // Call content generation service
  const response = await fetch(`${process.env.CONTENT_SERVICE_URL}/api/content/multiply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getServerSession().token}`
    },
    body: JSON.stringify({
      userId: session.user.id,
      sourceUrl: blogUrl,
      outputs: {
        socialImages: 5,
        videoClips: 3
      }
    })
  });

  return await response.json();
}
```

### Authentication Flow

```
User → swp-next (login)
         ↓
    JWT token generated
         ↓
swp-next → content-generation-service (with token)
         ↓
    Validate token
         ↓
    Process job
         ↓
    Return results
```

---

## Migration Strategy

For **Content Multiplier** (your most service-appropriate tool):

### Phase 1: Backend First
```bash
# Add to content-generation-service
POST /api/content/multiply

# Test with curl
curl -X POST https://content.superwebpros.com/api/content/multiply \
  -d '{"userId": "test", "sourceUrl": "...", "outputs": {...}}'
```

### Phase 2: Integrate with swp-next
```typescript
// Add to swp-next
import { generateContentMultiples } from '@/lib/content-service';

// Use in component
const result = await generateContentMultiples(blogUrl);
```

### Phase 3: Build UI
```typescript
// Full UI in swp-next
<ContentMultiplierTool />
  - Input form
  - SSE progress monitor
  - Asset gallery
  - Download/export options
```

---

## Anti-Patterns to Avoid

### ❌ Don't Put in Service If:
- Simple CRUD operations
- Just formatting data
- No heavy computation
- Only used in one place
- Needs tight coupling with UI

### ❌ Don't Put in Next.js If:
- Takes > 30 seconds
- Needs Python/specialized libs
- Resource-intensive
- Background processing
- Will be reused by other apps

---

## Your Immediate Action Items

### Short-term (Next.js tools)
1. Build Content Planner in swp-next
2. Build SEO Health Checker in swp-next
3. Build Journey Analyzer in swp-next
4. Build Analytics Dashboard in swp-next

**These are UI/analytics tools - belong in Next.js**

### Medium-term (Add to service)
When you're ready for Content Multiplier:
1. Add `/api/content/multiply` endpoint to content-generation-service
2. Orchestrate multiple AI services
3. Build UI in swp-next
4. Connect via API

### Long-term (More services)
As you identify heavy-compute tools:
- Video generation
- Batch processing
- Advanced AI features
- Add endpoints to content-generation-service

---

## Summary

**Simple rule:**

> **UI and fast logic → swp-next**
>
> **AI processing and slow jobs → content-generation-service**

**4 out of 5 tools** belong in swp-next because they're UI/analytics focused.

**Content Multiplier** is the exception - it's a perfect hybrid:
- UI in Next.js (where users interact)
- Processing in service (where AI happens)

**Your architecture is correct - most tools stay in swp-next, only heavy AI work goes to the service!**
