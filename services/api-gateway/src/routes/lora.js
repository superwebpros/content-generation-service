import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import Job from '../../../../shared/schemas/Job.js';
import { triggerTrainingWorker } from '../config/services.js';

const router = express.Router();

/**
 * @swagger
 * /api/lora/train:
 *   post:
 *     summary: Start a new LoRA training job
 *     description: Creates a new LoRA training job from a video URL. The job is queued and processed asynchronously.
 *     tags: [LoRA Training]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/TrainingRequest'
 *     responses:
 *       201:
 *         description: Training job created successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 jobId:
 *                   type: string
 *                   format: uuid
 *                 status:
 *                   type: string
 *                   example: queued
 *                 message:
 *                   type: string
 *                 data:
 *                   type: object
 *       400:
 *         description: Missing required fields
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       500:
 *         description: Server error
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
router.post('/train', async (req, res) => {
  try {
    const {
      userId,
      videoUrl,
      loraName,
      trigger = 'person',
      steps = 2500,
      learning_rate = 0.00009,
      webhookUrl
    } = req.body;

    // Validation
    if (!userId || !videoUrl || !loraName) {
      return res.status(400).json({
        error: 'Missing required fields: userId, videoUrl, loraName'
      });
    }

    // Create job record
    const jobId = uuidv4();
    const job = new Job({
      jobId,
      userId,
      type: 'lora-training',
      sourceVideo: {
        url: videoUrl,
        filename: videoUrl.split('/').pop() || 'video.mp4'
      },
      config: {
        loraName,
        trigger,
        steps,
        learning_rate
      },
      webhookUrl, // Optional webhook for notification
      status: 'queued',
      progress: 0
    });

    await job.save();

    // Trigger training worker
    try {
      await triggerTrainingWorker(jobId, {
        userId,
        videoUrl,
        loraName,
        trigger,
        steps,
        learning_rate
      });
    } catch (error) {
      // Worker failed to start, but job is queued
      // It can be retried later
      console.error('Failed to trigger training worker:', error.message);
    }

    res.status(201).json({
      jobId,
      status: 'queued',
      message: 'Training job created successfully',
      data: {
        loraName,
        trigger,
        steps
      }
    });

  } catch (error) {
    console.error('Error creating training job:', error);
    res.status(500).json({
      error: 'Failed to create training job',
      details: error.message
    });
  }
});

/**
 * @swagger
 * /api/lora/status/{jobId}:
 *   get:
 *     summary: Get status of a training job
 *     description: Returns current status, progress, and results (if completed) for a training job
 *     tags: [LoRA Training]
 *     parameters:
 *       - in: path
 *         name: jobId
 *         required: true
 *         schema:
 *           type: string
 *           format: uuid
 *         description: Job ID
 *     responses:
 *       200:
 *         description: Job status retrieved
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 jobId:
 *                   type: string
 *                 status:
 *                   type: string
 *                 progress:
 *                   type: integer
 *                 modelUrl:
 *                   type: string
 *                   description: Available when status is completed
 *       404:
 *         description: Job not found
 *       500:
 *         description: Server error
 */
router.get('/status/:jobId', async (req, res) => {
  try {
    const { jobId } = req.params;

    const job = await Job.findOne({ jobId });

    if (!job) {
      return res.status(404).json({
        error: 'Job not found'
      });
    }

    // Build response
    const response = {
      jobId: job.jobId,
      status: job.status,
      progress: job.progress,
      type: job.type,
      createdAt: job.createdAt,
      startedAt: job.startedAt,
      completedAt: job.completedAt
    };

    // Add output if completed
    if (job.status === 'completed' && job.versions.length > 0) {
      const latestVersion = job.versions[job.versions.length - 1];
      response.modelUrl = latestVersion.modelUrl;
      response.version = latestVersion.version;
    }

    // Add error if failed
    if (job.status === 'failed') {
      response.error = job.error;
    }

    res.json(response);

  } catch (error) {
    console.error('Error fetching job status:', error);
    res.status(500).json({
      error: 'Failed to fetch job status',
      details: error.message
    });
  }
});

/**
 * @swagger
 * /api/lora/list:
 *   get:
 *     summary: List all LORAs for a user
 *     description: Returns all LoRA training jobs for a specific user, optionally filtered by status
 *     tags: [LoRA Training]
 *     parameters:
 *       - in: query
 *         name: userId
 *         required: true
 *         schema:
 *           type: string
 *         description: User ID
 *       - in: query
 *         name: status
 *         required: false
 *         schema:
 *           type: string
 *           enum: [queued, processing, completed, failed]
 *         description: Filter by status
 *     responses:
 *       200:
 *         description: List of LORAs
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 total:
 *                   type: integer
 *                 loras:
 *                   type: array
 *                   items:
 *                     $ref: '#/components/schemas/Job'
 *       400:
 *         description: Missing userId parameter
 *       500:
 *         description: Server error
 */
router.get('/list', async (req, res) => {
  try {
    const { userId, status } = req.query;

    if (!userId) {
      return res.status(400).json({
        error: 'Missing required parameter: userId'
      });
    }

    // Build query
    const query = {
      userId,
      type: 'lora-training'
    };

    if (status) {
      query.status = status;
    }

    const jobs = await Job.find(query)
      .sort({ createdAt: -1 })
      .limit(100);

    // Format response
    const loras = jobs.map(job => ({
      jobId: job.jobId,
      loraName: job.config.loraName,
      trigger: job.config.trigger,
      status: job.status,
      progress: job.progress,
      versions: job.versions.length,
      latestVersion: job.versions.length > 0 ? {
        version: job.versions[job.versions.length - 1].version,
        modelUrl: job.versions[job.versions.length - 1].modelUrl,
        createdAt: job.versions[job.versions.length - 1].createdAt
      } : null,
      createdAt: job.createdAt,
      completedAt: job.completedAt
    }));

    res.json({
      total: loras.length,
      loras
    });

  } catch (error) {
    console.error('Error listing LORAs:', error);
    res.status(500).json({
      error: 'Failed to list LORAs',
      details: error.message
    });
  }
});

/**
 * GET /api/lora/:jobId
 * Get detailed information about a specific LORA
 */
router.get('/:jobId', async (req, res) => {
  try {
    const { jobId } = req.params;

    const job = await Job.findOne({ jobId, type: 'lora-training' });

    if (!job) {
      return res.status(404).json({
        error: 'LORA not found'
      });
    }

    res.json({
      jobId: job.jobId,
      userId: job.userId,
      loraName: job.config.loraName,
      trigger: job.config.trigger,
      config: job.config,
      sourceVideo: job.sourceVideo,
      versions: job.versions,
      status: job.status,
      progress: job.progress,
      error: job.error,
      usage: job.usage,
      createdAt: job.createdAt,
      startedAt: job.startedAt,
      completedAt: job.completedAt
    });

  } catch (error) {
    console.error('Error fetching LORA details:', error);
    res.status(500).json({
      error: 'Failed to fetch LORA details',
      details: error.message
    });
  }
});

export default router;
