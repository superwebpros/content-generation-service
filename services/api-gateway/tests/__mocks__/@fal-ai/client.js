/**
 * Mock for @fal-ai/client
 * Prevents real API calls during testing (saves money!)
 */

export const fal = {
  config: jest.fn(),

  subscribe: jest.fn().mockImplementation(async (endpoint, options) => {
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 100));

    // Mock different responses based on endpoint
    if (endpoint.includes('flux') || endpoint.includes('nano-banana')) {
      return {
        images: [{
          url: 'https://mock-fal-cdn.com/generated-image.png',
          width: 1024,
          height: 1024,
          content_type: 'image/png',
          file_size: 2500000
        }]
      };
    }

    if (endpoint.includes('lora')) {
      return {
        lora_url: 'https://mock-fal-cdn.com/trained-lora.safetensors',
        config_url: 'https://mock-fal-cdn.com/config.json',
        model_name: 'mock_lora'
      };
    }

    return { images: [] };
  }),

  storage: {
    upload: jest.fn().mockResolvedValue('https://mock-fal-storage.com/uploaded-image.jpg')
  }
};
