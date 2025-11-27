/**
 * Input validation and transformation for image generation models
 */

import { getModelConfig } from './registry.js';

/**
 * Validate request inputs based on model requirements
 */
export function validateRequest(model, inputs) {
  const modelConfig = getModelConfig(model);

  // Check all required inputs are present
  for (const required of modelConfig.requiredInputs) {
    if (!inputs[required] && inputs[required] !== 0) {
      throw new Error(`Missing required input for ${model}: ${required}`);
    }
  }

  // Validate specific input types
  if (inputs.prompt && typeof inputs.prompt !== 'string') {
    throw new Error('prompt must be a string');
  }

  if (inputs.image_url && typeof inputs.image_url !== 'string') {
    throw new Error('image_url must be a valid URL string');
  }

  if (inputs.image_urls && !Array.isArray(inputs.image_urls)) {
    throw new Error('image_urls must be an array');
  }

  if (inputs.loras) {
    if (!Array.isArray(inputs.loras)) {
      throw new Error('loras must be an array');
    }
    for (const lora of inputs.loras) {
      if (!lora.path) {
        throw new Error('Each LoRA must have a path property');
      }
    }
  }

  return modelConfig;
}

/**
 * Transform inputs into fal.ai format
 */
export function transformInputsForFal(model, inputs, options = {}) {
  const modelConfig = getModelConfig(model);

  // Start with default options for this model
  const falRequest = { ...modelConfig.defaultOptions };

  // Add all provided inputs
  Object.keys(inputs).forEach(key => {
    if (inputs[key] !== undefined && inputs[key] !== null) {
      falRequest[key] = inputs[key];
    }
  });

  // Override with user-provided options
  if (options) {
    // Handle aspect_ratio
    if (options.aspect_ratio) {
      falRequest.aspect_ratio = options.aspect_ratio;
    }

    // Handle resolution
    if (options.resolution) {
      falRequest.resolution = options.resolution;
    }

    // Handle image_size (width/height)
    if (options.width || options.height) {
      falRequest.image_size = {
        width: options.width || 1024,
        height: options.height || 1024
      };
      // Remove aspect_ratio if explicit dimensions provided
      delete falRequest.aspect_ratio;
    }

    // Handle num_images
    if (options.num_images) {
      falRequest.num_images = options.num_images;
    }

    // Handle seed
    if (options.seed !== undefined) {
      falRequest.seed = options.seed;
    }

    // Handle output_format
    if (options.output_format) {
      falRequest.output_format = options.output_format;
    }
  }

  return falRequest;
}

/**
 * Estimate cost for a generation request
 */
export function estimateCost(model, options = {}) {
  const modelConfig = getModelConfig(model);
  const numImages = options.num_images || 1;

  return {
    costPerImage: modelConfig.costPerImage,
    totalCost: modelConfig.costPerImage * numImages,
    numImages
  };
}
