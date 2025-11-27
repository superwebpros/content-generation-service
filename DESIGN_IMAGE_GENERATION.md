# Image Generation Service - Design Document

## Architecture: Model Registry Pattern

### Problem
fal.ai has many models with different input requirements. We need a flexible API that:
- Works with any current or future fal.ai model
- Validates inputs based on model type
- Doesn't require new routes for each model
- Maintains type safety and documentation

### Solution: Unified Generation Endpoint + Model Registry

## API Design

### Single Endpoint for All Models

```
POST /api/images/generate
```

**Request Schema:**
```typescript
{
  model: string;           // Model identifier (e.g., "flux-pro", "face-swap")
  inputs: {                // Model-specific inputs (flexible)
    prompt?: string;
    image_url?: string;
    lora_url?: string;
    lora_scale?: number;
    // ... any model-specific parameters
  };
  options?: {              // Common options across all models
    width?: number;
    height?: number;
    num_images?: number;
    seed?: number;
  };
  userId: string;          // For tracking/billing
}
```

### Model Registry

**Registry defines each model's capabilities:**

```javascript
// services/image-generation/models/registry.js

export const MODEL_REGISTRY = {
  'flux-pro': {
    falEndpoint: 'fal-ai/flux-pro',
    requiredInputs: ['prompt'],
    optionalInputs: ['image_url', 'strength'],
    supportsLora: false,
    costPerImage: 0.05,
    description: 'High-quality FLUX Pro model'
  },

  'flux-dev': {
    falEndpoint: 'fal-ai/flux/dev',
    requiredInputs: ['prompt'],
    optionalInputs: ['image_url', 'strength'],
    supportsLora: true,
    costPerImage: 0.03,
    description: 'Fast FLUX Dev model with LoRA support'
  },

  'flux-lora': {
    falEndpoint: 'fal-ai/flux-lora',
    requiredInputs: ['prompt', 'lora_url'],
    optionalInputs: ['image_url', 'lora_scale', 'strength'],
    supportsLora: true,
    costPerImage: 0.03,
    description: 'FLUX with custom LoRA'
  },

  'face-swap': {
    falEndpoint: 'fal-ai/face-swap',
    requiredInputs: ['image_url', 'target_image_url'],
    optionalInputs: ['prompt'],
    supportsLora: false,
    costPerImage: 0.02,
    description: 'Face swapping model'
  },

  'image-to-image': {
    falEndpoint: 'fal-ai/flux/dev/image-to-image',
    requiredInputs: ['prompt', 'image_url'],
    optionalInputs: ['strength', 'guidance_scale'],
    supportsLora: false,
    costPerImage: 0.03,
    description: 'Transform existing images'
  }
};
```

## Implementation Layers

### Layer 1: Model Validator

```javascript
// services/image-generation/models/validator.js

export function validateRequest(model, inputs) {
  const modelConfig = MODEL_REGISTRY[model];

  if (!modelConfig) {
    throw new Error(`Unknown model: ${model}`);
  }

  // Check required inputs
  for (const required of modelConfig.requiredInputs) {
    if (!inputs[required]) {
      throw new Error(`Missing required input: ${required}`);
    }
  }

  // Validate input types
  // ... type checking logic

  return modelConfig;
}
```

### Layer 2: Input Transformer

```javascript
// services/image-generation/models/transformer.js

export function transformInputsForFal(model, inputs, options) {
  const modelConfig = MODEL_REGISTRY[model];

  // Build fal.ai request based on model
  const falRequest = {
    prompt: inputs.prompt || '',
  };

  // Add model-specific parameters
  if (inputs.image_url) {
    falRequest.image_url = inputs.image_url;
  }

  if (inputs.lora_url && modelConfig.supportsLora) {
    falRequest.loras = [{
      path: inputs.lora_url,
      scale: inputs.lora_scale || 1.0
    }];
  }

  // Add common options
  if (options) {
    falRequest.image_size = {
      width: options.width || 1024,
      height: options.height || 1024
    };
    falRequest.num_images = options.num_images || 1;
  }

  return falRequest;
}
```

### Layer 3: fal.ai Client

```javascript
// services/image-generation/providers/fal-client.js

import * as fal from '@fal-ai/serverless-client';

export class FalImageGenerator {
  constructor(apiKey) {
    fal.config({ credentials: apiKey });
  }

  async generate(modelConfig, transformedInputs) {
    try {
      const result = await fal.subscribe(modelConfig.falEndpoint, {
        input: transformedInputs,
        logs: true,
        onQueueUpdate: (update) => {
          // Could send progress updates here
          console.log('Queue update:', update);
        }
      });

      return result;

    } catch (error) {
      console.error('fal.ai error:', error);
      throw error;
    }
  }
}
```

### Layer 4: Route Handler

```javascript
// services/api-gateway/src/routes/images.js

router.post('/generate', async (req, res) => {
  try {
    const { model, inputs, options, userId } = req.body;

    // 1. Validate request
    const modelConfig = validateRequest(model, inputs);

    // 2. Create job in MongoDB
    const jobId = uuidv4();
    const job = new Job({
      jobId,
      userId,
      type: 'image-generation',
      config: {
        model,
        inputs,
        options
      },
      status: 'queued'
    });
    await job.save();

    // 3. Transform inputs for fal.ai
    const falInputs = transformInputsForFal(model, inputs, options);

    // 4. Call fal.ai
    const result = await falClient.generate(modelConfig, falInputs);

    // 5. Upload result to S3
    const imageUrl = await uploadImageToS3(result.images[0], userId, jobId);

    // 6. Update MongoDB
    await updateJobWithResult(jobId, imageUrl, result);

    res.json({
      jobId,
      status: 'completed',
      imageUrl,
      cost: modelConfig.costPerImage
    });

  } catch (error) {
    // Error handling
  }
});
```

## Usage Examples

### Simple Text-to-Image
```bash
curl -X POST /api/images/generate \
  -d '{
    "model": "flux-pro",
    "inputs": {
      "prompt": "A professional headshot"
    },
    "userId": "user123"
  }'
```

### Image-to-Image with LoRA
```bash
curl -X POST /api/images/generate \
  -d '{
    "model": "flux-lora",
    "inputs": {
      "prompt": "Professional headshot of jf in a suit",
      "image_url": "s3://bucket/reference.jpg",
      "lora_url": "s3://bucket/loras/jesse_avatar.safetensors",
      "lora_scale": 0.8
    },
    "options": {
      "width": 1024,
      "height": 1024
    },
    "userId": "user123"
  }'
```

### Face Swap
```bash
curl -X POST /api/images/generate \
  -d '{
    "model": "face-swap",
    "inputs": {
      "image_url": "s3://bucket/source.jpg",
      "target_image_url": "s3://bucket/face.jpg"
    },
    "userId": "user123"
  }'
```

## Benefits of This Design

### 1. Extensibility
Add new models by just updating the registry:
```javascript
MODEL_REGISTRY['new-model'] = {
  falEndpoint: 'fal-ai/new-endpoint',
  requiredInputs: ['prompt'],
  // ...
};
```

### 2. Type Safety
Pydantic/Joi validation based on model:
```javascript
function getValidationSchema(model) {
  const config = MODEL_REGISTRY[model];

  return Joi.object({
    ...config.requiredInputs.reduce((acc, input) => {
      acc[input] = Joi.string().required();
      return acc;
    }, {}),
    // ... optional inputs
  });
}
```

### 3. Swagger Documentation
Single endpoint, all models documented:
```yaml
/api/images/generate:
  post:
    parameters:
      - name: model
        enum: [flux-pro, flux-dev, flux-lora, face-swap, ...]
    requestBody:
      # Different schemas shown based on model selection
```

### 4. Billing/Usage Tracking
Easy to track costs:
```javascript
const modelConfig = MODEL_REGISTRY[model];
await updateUserBilling(userId, {
  cost: modelConfig.costPerImage * numImages,
  model,
  jobId
});
```

## Alternative: Template-Based Approach

If you want even more flexibility for your specific use cases (billboard, discount banners, etc.):

```javascript
// Higher-level templates that use models under the hood
POST /api/templates/billboard
POST /api/templates/discount-banner
POST /api/templates/product-shot

// Each template knows which model(s) to use
{
  "template": "billboard",
  "variables": {
    "headline": "Winter Sale",
    "background_style": "snowy",
    "avatar_lora": "s3://..."
  }
}
```

This gives you **business-level abstractions** on top of model-level abstractions.

---

## My Recommendation

**Start with the Model Registry pattern** because:
1. Flexible enough for any fal.ai model
2. Single endpoint = simple API
3. Easy to add templates layer later
4. Swagger docs stay clean
5. Matches your existing fal.ai scripts

**Then add Templates** as you identify common patterns (billboard, discount, etc.)

**Want me to implement the image generation service with the Model Registry pattern?**