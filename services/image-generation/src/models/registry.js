/**
 * Model Registry - Defines all available fal.ai models and their capabilities
 *
 * This registry pattern allows us to:
 * - Add new models without changing route code
 * - Validate inputs based on model requirements
 * - Track costs per model
 * - Document capabilities
 */

export const MODEL_REGISTRY = {
  // Image editing with nano-banana-pro (what you're currently using)
  'nano-banana-edit': {
    falEndpoint: 'fal-ai/nano-banana-pro/edit',
    category: 'image-editing',
    requiredInputs: ['prompt', 'image_urls'],
    optionalInputs: ['num_images', 'aspect_ratio', 'resolution', 'output_format'],
    defaultOptions: {
      num_images: 1,
      aspect_ratio: '1:1',
      resolution: '2K',
      output_format: 'png'
    },
    supportsMultipleImages: true, // Can take multiple reference images
    costPerImage: 0.02,
    description: 'Edit existing images with AI - supports multi-image input for style transfer'
  },

  // FLUX models
  'flux-pro': {
    falEndpoint: 'fal-ai/flux-pro',
    category: 'text-to-image',
    requiredInputs: ['prompt'],
    optionalInputs: ['image_size', 'num_images', 'seed'],
    defaultOptions: {
      image_size: { width: 1024, height: 1024 },
      num_images: 1
    },
    supportsMultipleImages: false,
    supportsLora: false,
    costPerImage: 0.05,
    description: 'Highest quality FLUX model for professional images'
  },

  'flux-dev': {
    falEndpoint: 'fal-ai/flux/dev',
    category: 'text-to-image',
    requiredInputs: ['prompt'],
    optionalInputs: ['image_size', 'num_images', 'seed', 'guidance_scale'],
    defaultOptions: {
      image_size: { width: 1024, height: 1024 },
      num_images: 1,
      guidance_scale: 3.5
    },
    supportsMultipleImages: false,
    supportsLora: true,
    costPerImage: 0.03,
    description: 'Fast FLUX dev model with LoRA support'
  },

  'flux-lora': {
    falEndpoint: 'fal-ai/flux-lora',
    category: 'text-to-image',
    requiredInputs: ['prompt', 'loras'], // loras is array of {path, scale}
    optionalInputs: ['image_size', 'num_images', 'seed'],
    defaultOptions: {
      image_size: { width: 1024, height: 1024 },
      num_images: 1
    },
    supportsMultipleImages: false,
    supportsLora: true,
    costPerImage: 0.03,
    description: 'FLUX with custom LoRA models'
  },

  'flux-dev-image-to-image': {
    falEndpoint: 'fal-ai/flux/dev/image-to-image',
    category: 'image-to-image',
    requiredInputs: ['prompt', 'image_url'],
    optionalInputs: ['strength', 'num_images', 'seed'],
    defaultOptions: {
      strength: 0.95,
      num_images: 1
    },
    supportsMultipleImages: false,
    supportsLora: true,
    costPerImage: 0.03,
    description: 'Transform existing images with FLUX'
  },

  // Face-specific models
  'face-swap': {
    falEndpoint: 'fal-ai/face-swap',
    category: 'face-manipulation',
    requiredInputs: ['image_url', 'swap_image_url'],
    optionalInputs: [],
    defaultOptions: {},
    supportsMultipleImages: false,
    supportsLora: false,
    costPerImage: 0.02,
    description: 'Swap faces between two images'
  }
};

/**
 * Get model configuration
 */
export function getModelConfig(modelName) {
  const config = MODEL_REGISTRY[modelName];
  if (!config) {
    throw new Error(`Unknown model: ${modelName}. Available models: ${Object.keys(MODEL_REGISTRY).join(', ')}`);
  }
  return config;
}

/**
 * Get all models by category
 */
export function getModelsByCategory(category) {
  return Object.entries(MODEL_REGISTRY)
    .filter(([_, config]) => config.category === category)
    .map(([name, config]) => ({ name, ...config }));
}

/**
 * List all available models
 */
export function listModels() {
  return Object.entries(MODEL_REGISTRY).map(([name, config]) => ({
    name,
    category: config.category,
    description: config.description,
    requiredInputs: config.requiredInputs,
    optionalInputs: config.optionalInputs,
    costPerImage: config.costPerImage
  }));
}
