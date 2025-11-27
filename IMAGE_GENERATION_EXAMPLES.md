# Image Generation Service - Usage Examples

## Model Registry Pattern

The service uses a **unified endpoint** that works with any fal.ai model. Just specify the model name and provide the appropriate inputs.

## Available Models

```bash
curl http://localhost:5000/api/images/models | jq .
```

Current models:
- `nano-banana-edit` - Edit existing images (what your scripts use)
- `flux-pro` - High-quality text-to-image
- `flux-dev` - Fast text-to-image with LoRA support
- `flux-lora` - Text-to-image with custom LoRAs
- `flux-dev-image-to-image` - Transform existing images
- `face-swap` - Swap faces between images

## Basic Usage

### 1. Simple Text-to-Image

```bash
curl -X POST http://localhost:5000/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-pro",
    "inputs": {
      "prompt": "A professional headshot of a business consultant"
    },
    "userId": "user123"
  }'
```

### 2. Image Editing (Like Your Billboard Script)

```bash
curl -X POST http://localhost:5000/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nano-banana-edit",
    "inputs": {
      "prompt": "Transform this billboard for an SEO workshop. Change text to: THE DEFINITIVE MULTIMODAL SEO WORKSHOP",
      "image_urls": ["https://your-template.jpg"]
    },
    "options": {
      "aspect_ratio": "9:16",
      "resolution": "2K"
    },
    "userId": "user123"
  }'
```

### 3. Face Swap with Multiple Reference Images (Like Your Scripts)

```bash
curl -X POST http://localhost:5000/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nano-banana-edit",
    "inputs": {
      "prompt": "Replace the person in the second image with the person from the first image, keeping the same pose and lighting",
      "image_urls": [
        "https://s3.../jesse-reference.jpg",
        "https://s3.../ad-template.jpg"
      ]
    },
    "options": {
      "aspect_ratio": "1:1",
      "resolution": "2K",
      "output_format": "png"
    },
    "userId": "user123"
  }'
```

### 4. Using Custom LoRAs

```bash
curl -X POST http://localhost:5000/api/images/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-lora",
    "inputs": {
      "prompt": "Professional headshot of jf in a suit",
      "loras": [{
        "path": "https://content-generation-assets.s3.amazonaws.com/loras/user/job/v1/model.safetensors",
        "scale": 0.8
      }]
    },
    "options": {
      "width": 1024,
      "height": 1024
    },
    "userId": "user123"
  }'
```

## Migrating Your Existing Scripts

### Before (Your billboard script)
```javascript
const result = await fal.subscribe("fal-ai/nano-banana-pro/edit", {
  input: {
    prompt: prompt,
    image_urls: [imageUrl],
    num_images: 1,
    aspect_ratio: "9:16",
    resolution: "2K"
  }
});
```

### After (Using the service)
```javascript
const response = await fetch('http://localhost:5000/api/images/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'nano-banana-edit',
    inputs: {
      prompt: prompt,
      image_urls: [imageUrl]
    },
    options: {
      aspect_ratio: '9:16',
      resolution: '2K',
      num_images: 1
    },
    userId: 'your-user-id'
  })
});

const result = await response.json();
console.log('Generated:', result.images[0].url);
```

## Benefits of Using the Service

1. **Centralized Storage**: Images automatically uploaded to your S3
2. **Job Tracking**: Every generation tracked in MongoDB
3. **Usage Billing**: Costs tracked per user
4. **History**: Access all past generations
5. **Reusable**: Call from any app/script
6. **Scalable**: Add queue for high volume

## Batch Generation

For your `generate-all-lora.js` workflow:

```javascript
const variants = [/* your variants */];

for (const variant of variants) {
  const response = await fetch('http://localhost:5000/api/images/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: 'nano-banana-edit',
      inputs: {
        prompt: variant.prompt,
        image_urls: [jesseUrl, templateUrl]
      },
      options: {
        aspect_ratio: '1:1',
        resolution: '2K'
      },
      userId: 'campaign-seo-workshop'
    })
  });

  const result = await response.json();
  console.log(`✅ ${variant.name}:`, result.images[0].url);
}
```

## Retrieving Results

### Get specific job
```bash
curl http://localhost:5000/api/jobs/{jobId} | jq .
```

### List all image generation jobs for a user
```bash
curl "http://localhost:5000/api/jobs?userId=user123&type=image-generation" | jq .
```

### List all completed jobs
```bash
curl "http://localhost:5000/api/jobs?userId=user123&status=completed" | jq .
```

## Cost Estimation

Before generating, estimate costs:

```bash
curl -X POST http://localhost:5000/api/images/estimate-cost \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-pro",
    "options": {
      "num_images": 10
    }
  }'
```

Response:
```json
{
  "costPerImage": 0.05,
  "totalCost": 0.50,
  "numImages": 10
}
```

## Adding New Models

Simply update the registry in `services/image-generation/src/models/registry.js`:

```javascript
'your-new-model': {
  falEndpoint: 'fal-ai/your-endpoint',
  category: 'text-to-image',
  requiredInputs: ['prompt'],
  optionalInputs: ['seed', 'guidance_scale'],
  defaultOptions: {
    num_images: 1
  },
  costPerImage: 0.03,
  description: 'Your model description'
}
```

No route changes needed!

## Error Handling

The service handles errors gracefully:
- Invalid model → 400 error with list of valid models
- Missing required inputs → 400 error specifying what's missing
- fal.ai API errors → 500 error with details
- Jobs marked as 'failed' in MongoDB with error message

## Monitoring

Check Swagger docs: http://localhost:5000/api-docs

All image generation endpoints are documented with:
- Request schemas
- Response formats
- Error codes
- Example values
