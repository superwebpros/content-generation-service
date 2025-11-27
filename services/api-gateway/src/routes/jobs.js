import express from 'express';
import Job from '../../../../shared/schemas/Job.js';

const router = express.Router();

/**
 * @swagger
 * /api/jobs/{jobId}:
 *   get:
 *     summary: Get any job by ID (all types)
 *     description: Returns job details for any job type (lora-training, image-generation, etc.)
 *     tags: [Jobs]
 *     parameters:
 *       - in: path
 *         name: jobId
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Job details
 *       404:
 *         description: Job not found
 */
router.get('/:jobId', async (req, res) => {
  try {
    const { jobId } = req.params;

    const job = await Job.findOne({ jobId });

    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    res.json(job);

  } catch (error) {
    console.error('Error fetching job:', error);
    res.status(500).json({
      error: 'Failed to fetch job',
      details: error.message
    });
  }
});

/**
 * @swagger
 * /api/jobs:
 *   get:
 *     summary: List all jobs for a user
 *     description: Returns all jobs (all types) for a user, optionally filtered by type and status
 *     tags: [Jobs]
 *     parameters:
 *       - in: query
 *         name: userId
 *         required: true
 *         schema:
 *           type: string
 *       - in: query
 *         name: type
 *         schema:
 *           type: string
 *           enum: [lora-training, image-generation, video-generation]
 *       - in: query
 *         name: status
 *         schema:
 *           type: string
 *           enum: [queued, processing, completed, failed]
 *     responses:
 *       200:
 *         description: List of jobs
 *       400:
 *         description: Missing userId
 */
router.get('/', async (req, res) => {
  try {
    const { userId, type, status } = req.query;

    if (!userId) {
      return res.status(400).json({ error: 'userId is required' });
    }

    const query = { userId };

    if (type) {
      query.type = type;
    }

    if (status) {
      query.status = status;
    }

    const jobs = await Job.find(query)
      .sort({ createdAt: -1 })
      .limit(100);

    res.json({
      total: jobs.length,
      jobs
    });

  } catch (error) {
    console.error('Error listing jobs:', error);
    res.status(500).json({
      error: 'Failed to list jobs',
      details: error.message
    });
  }
});

export default router;
