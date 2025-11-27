import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import Job from '../../../../shared/schemas/Job.js';
import { uploadFile } from '../../../../shared/storage/s3-client.js';
import { fal } from '@fal-ai/client';
import { Blob } from 'buffer';

// Import from image-generation service
import { getModelConfig, listModels } from '../../../image-generation/src/models/registry.js';
import { validateRequest, transformInputsForFal, estimateCost } from '../../../image-generation/src/models/validator.js';

const router = express.Router();

// Configure fal.ai
fal.config({ credentials: process.env.FAL_KEY });

/**
 * @swagger
 * /api/images/models:
 *   get:
 *     summary: List all available image generation models
 *     description: Returns information about all registered fal.ai models
 *     tags: [Image Generation]
 *     responses:
 *       200:
 *         description: List of available models
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 total:
 *                   type: integer
 *                 models:
 *                   type: array
 */
router.get('/models', async (req, res) => {
  try {
    const models = listModels();

    res.json({
      total: models.length,
      models
    });

  } catch (error) {
    console.error('Error listing models:', error);
    res.status(500).json({
      error: 'Failed to list models',
      details: error.message
    });
  }
});

/**
 * @swagger
 * /api/images/generate:
 *   post:
 *     summary: Generate images using any registered model
 *     description: Unified endpoint for all image generation models. Validates inputs based on selected model.
 *     tags: [Image Generation]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - model
 *               - inputs
 *               - userId
 *             properties:
 *               model:
 *                 type: string
 *                 description: Model identifier (e.g., flux-pro, nano-banana-edit)
 *                 example: nano-banana-edit
 *               inputs:
 *                 type: object
 *                 description: Model-specific inputs (varies by model)
 *                 example:
 *                   prompt: "A professional headshot"
 *                   image_urls: ["https://..."]
 *               options:
 *                 type: object
 *                 description: Optional generation parameters
 *                 properties:
 *                   width:
 *                     type: integer
 *                   height:
 *                     type: integer
 *                   num_images:
 *                     type: integer
 *                   seed:
 *                     type: integer
 *               userId:
 *                 type: string
 *     responses:
 *       201:
 *         description: Image generation successful
 *       400:
 *         description: Invalid request
 *       500:
 *         description: Generation failed
 */
router.post('/generate', async (req, res) => {
  try {
    const { model, inputs, options = {}, userId } = req.body;

    // Validation
    if (!userId) {
      return res.status(400).json({ error: 'userId is required' });
    }

    if (!model) {
      return res.status(400).json({ error: 'model is required' });
    }

    if (!inputs) {
      return res.status(400).json({ error: 'inputs is required' });
    }

    // Validate against model requirements
    const modelConfig = validateRequest(model, inputs);

    // Estimate cost
    const costEstimate = estimateCost(model, options);

    // Create job in MongoDB
    const jobId = uuidv4();
    const job = new Job({
      jobId,
      userId,
      type: 'image-generation',
      config: {
        model,
        inputs,
        options,
        estimatedCost: costEstimate.totalCost
      },
      status: 'processing',
      progress: 0
    });

    await job.save();

    // Transform inputs for fal.ai
    const falInputs = transformInputsForFal(model, inputs, options);

    console.log(`🎨 Generating image with ${model}`);
    console.log(`   Job ID: ${jobId}`);
    console.log(`   Estimated cost: $${costEstimate.totalCost}`);

    // Call fal.ai
    await job.updateOne({ $set: { progress: 50 } });

    const result = await fal.subscribe(modelConfig.falEndpoint, {
      input: falInputs,
      logs: true,
      onQueueUpdate: (update) => {
        if (update.status === 'IN_PROGRESS') {
          console.log(`   Generation in progress...`);
        }
      }
    });

    console.log(`   ✅ Generation complete`);

    // Download and upload to our S3
    await job.updateOne({ $set: { progress: 75 } });

    const generatedImages = [];

    if (result.images && result.images.length > 0) {
      for (let i = 0; i < result.images.length; i++) {
        const imageData = result.images[i];

        // Download from fal.ai
        const response = await fetch(imageData.url);
        const arrayBuffer = await response.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);

        // Upload to our S3
        const imageFilename = `image_${i + 1}.${options.output_format || 'png'}`;
        const s3Key = `generated-images/${userId}/${jobId}/${imageFilename}`;
        const s3Url = await uploadFile(s3Key, buffer, imageData.content_type || 'image/png');

        console.log(`   ☁️  Uploaded to S3: ${s3Url}`);

        generatedImages.push({
          url: s3Url,
          s3Key,
          width: imageData.width,
          height: imageData.height,
          contentType: imageData.content_type,
          sizeBytes: buffer.length
        });
      }
    }

    // Update job with results
    const totalSize = generatedImages.reduce((sum, img) => sum + img.sizeBytes, 0);

    await job.updateOne({
      $set: {
        status: 'completed',
        progress: 100,
        completedAt: new Date(),
        'usage.storageBytes': totalSize,
        'usage.lastUsed': new Date()
      },
      $push: {
        versions: {
          version: 1,
          images: generatedImages,
          createdAt: new Date(),
          config: { model, inputs, options }
        }
      }
    });

    res.status(201).json({
      jobId,
      status: 'completed',
      images: generatedImages,
      cost: costEstimate.totalCost,
      message: 'Image generation successful'
    });

  } catch (error) {
    console.error('Image generation error:', error);

    // Try to update job status if we have a jobId
    const jobId = req.body?.jobId;
    if (jobId) {
      await Job.updateOne(
        { jobId },
        {
          $set: {
            status: 'failed',
            error: error.message
          }
        }
      ).catch(err => console.error('Failed to update job:', err));
    }

    res.status(500).json({
      error: 'Image generation failed',
      details: error.message
    });
  }
});

/**
 * @swagger
 * /api/images/estimate-cost:
 *   post:
 *     summary: Estimate cost for an image generation request
 *     tags: [Image Generation]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               model:
 *                 type: string
 *               options:
 *                 type: object
 *                 properties:
 *                   num_images:
 *                     type: integer
 *     responses:
 *       200:
 *         description: Cost estimate
 */
router.post('/estimate-cost', async (req, res) => {
  try {
    const { model, options = {} } = req.body;

    if (!model) {
      return res.status(400).json({ error: 'model is required' });
    }

    const estimate = estimateCost(model, options);

    res.json(estimate);

  } catch (error) {
    res.status(400).json({
      error: 'Invalid model',
      details: error.message
    });
  }
});

export default router;
