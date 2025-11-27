import swaggerJsdoc from 'swagger-jsdoc';
import swaggerUi from 'swagger-ui-express';

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Content Generation Service API',
      version: '1.0.0',
      description: 'AI-powered content generation services including LoRA training, image generation, and video processing',
      contact: {
        name: 'SuperWebPros',
        url: 'https://superwebpros.com'
      }
    },
    servers: [
      {
        url: 'http://localhost:5000',
        description: 'Development server'
      },
      {
        url: 'https://content.superwebpros.com',
        description: 'Production server'
      }
    ],
    components: {
      schemas: {
        Job: {
          type: 'object',
          properties: {
            jobId: {
              type: 'string',
              format: 'uuid',
              description: 'Unique job identifier'
            },
            userId: {
              type: 'string',
              description: 'User who created the job'
            },
            type: {
              type: 'string',
              enum: ['lora-training', 'image-generation', 'video-generation'],
              description: 'Type of content generation job'
            },
            status: {
              type: 'string',
              enum: ['queued', 'processing', 'completed', 'failed'],
              description: 'Current job status'
            },
            progress: {
              type: 'integer',
              minimum: 0,
              maximum: 100,
              description: 'Job progress percentage'
            },
            createdAt: {
              type: 'string',
              format: 'date-time'
            },
            completedAt: {
              type: 'string',
              format: 'date-time',
              nullable: true
            }
          }
        },
        TrainingRequest: {
          type: 'object',
          required: ['userId', 'videoUrl', 'loraName'],
          properties: {
            userId: {
              type: 'string',
              description: 'User identifier'
            },
            videoUrl: {
              type: 'string',
              format: 'uri',
              description: 'URL to source video (HTTP/HTTPS or S3)'
            },
            loraName: {
              type: 'string',
              description: 'Name for the LoRA model'
            },
            trigger: {
              type: 'string',
              default: 'person',
              description: 'Trigger phrase for the LoRA'
            },
            steps: {
              type: 'integer',
              default: 2500,
              description: 'Training steps'
            },
            learning_rate: {
              type: 'number',
              default: 0.00009,
              description: 'Learning rate for training'
            }
          }
        },
        Error: {
          type: 'object',
          properties: {
            error: {
              type: 'string',
              description: 'Error message'
            },
            details: {
              type: 'string',
              description: 'Detailed error information'
            }
          }
        }
      },
      securitySchemes: {
        ApiKeyAuth: {
          type: 'apiKey',
          in: 'header',
          name: 'X-API-Key',
          description: 'API key for authentication (future implementation)'
        }
      }
    }
  },
  apis: ['./src/routes/*.js'], // Path to API routes
};

const specs = swaggerJsdoc(options);

export { specs, swaggerUi };
