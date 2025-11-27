import express from 'express';
import Job from '../../../../shared/schemas/Job.js';

const router = express.Router();

/**
 * @swagger
 * /api/assets/loras:
 *   get:
 *     summary: List all LoRAs for a user
 *     description: Returns formatted list of trained LoRA models with latest version info
 *     tags: [Assets]
 *     parameters:
 *       - in: query
 *         name: userId
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: List of LoRAs
 */
router.get('/loras', async (req, res) => {
  try {
    const { userId } = req.query;

    if (!userId) {
      return res.status(400).json({ error: 'userId is required' });
    }

    const jobs = await Job.find({
      userId,
      type: 'lora-training',
      status: 'completed'
    }).sort({ createdAt: -1 });

    const loras = jobs.map(job => {
      const latestVersion = job.versions[job.versions.length - 1] || {};

      return {
        loraId: job.jobId,
        name: job.config.loraName,
        trigger: job.config.trigger,
        totalVersions: job.versions.length,
        latestVersion: {
          version: latestVersion.version,
          modelUrl: latestVersion.modelUrl,
          sizeBytes: latestVersion.sizeBytes,
          createdAt: latestVersion.createdAt
        },
        sourceVideo: job.sourceVideo?.filename,
        createdAt: job.createdAt,
        lastUsed: job.usage?.lastUsed
      };
    });

    res.json({
      total: loras.length,
      loras
    });

  } catch (error) {
    console.error('Error listing LORAs:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/assets/images:
 *   get:
 *     summary: List all generated images for a user
 *     description: Returns formatted list of AI-generated images
 *     tags: [Assets]
 *     parameters:
 *       - in: query
 *         name: userId
 *         required: true
 *         schema:
 *           type: string
 *       - in: query
 *         name: model
 *         schema:
 *           type: string
 *         description: Filter by model (flux-pro, nano-banana-edit, etc.)
 *     responses:
 *       200:
 *         description: List of images
 */
router.get('/images', async (req, res) => {
  try {
    const { userId, model } = req.query;

    if (!userId) {
      return res.status(400).json({ error: 'userId is required' });
    }

    const query = {
      userId,
      type: 'image-generation',
      status: 'completed'
    };

    if (model) {
      query['config.model'] = model;
    }

    const jobs = await Job.find(query).sort({ createdAt: -1 });

    const images = jobs.flatMap(job => {
      const version = job.versions[0] || {};
      const imageList = version.images || [];

      return imageList.map((img, idx) => ({
        imageId: `${job.jobId}_${idx}`,
        jobId: job.jobId,
        model: job.config.model,
        prompt: job.config.inputs?.prompt,
        imageUrl: img.url,
        s3Key: img.s3Key,
        width: img.width,
        height: img.height,
        sizeBytes: img.sizeBytes,
        createdAt: job.createdAt
      }));
    });

    res.json({
      total: images.length,
      images
    });

  } catch (error) {
    console.error('Error listing images:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/assets/transcripts:
 *   get:
 *     summary: List all transcripts for a user
 *     description: Returns formatted list of audio/video transcriptions
 *     tags: [Assets]
 *     parameters:
 *       - in: query
 *         name: userId
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: List of transcripts
 */
router.get('/transcripts', async (req, res) => {
  try {
    const { userId } = req.query;

    if (!userId) {
      return res.status(400).json({ error: 'userId is required' });
    }

    const jobs = await Job.find({
      userId,
      type: 'transcription',
      status: 'completed'
    }).sort({ createdAt: -1 });

    const transcripts = jobs.map(job => {
      const version = job.versions[0] || {};

      return {
        transcriptId: job.jobId,
        fileName: job.sourceVideo?.filename,
        audioUrl: job.sourceVideo?.url,
        transcriptUrl: version.transcriptUrl,
        textUrl: version.textUrl,
        wordCount: version.wordCount,
        duration: version.duration,
        createdAt: job.createdAt
      };
    });

    res.json({
      total: transcripts.length,
      transcripts
    });

  } catch (error) {
    console.error('Error listing transcripts:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/assets/search:
 *   get:
 *     summary: Search across all asset types
 *     description: Full-text search across jobs (searches config, filenames, etc.)
 *     tags: [Assets]
 *     parameters:
 *       - in: query
 *         name: userId
 *         required: true
 *         schema:
 *           type: string
 *       - in: query
 *         name: q
 *         required: true
 *         schema:
 *           type: string
 *         description: Search query
 *     responses:
 *       200:
 *         description: Search results
 */
router.get('/search', async (req, res) => {
  try {
    const { userId, q } = req.query;

    if (!userId || !q) {
      return res.status(400).json({ error: 'userId and q are required' });
    }

    // MongoDB text search (basic - could enhance with Typesense later)
    const jobs = await Job.find({
      userId,
      status: 'completed',
      $or: [
        { 'config.loraName': { $regex: q, $options: 'i' } },
        { 'sourceVideo.filename': { $regex: q, $options: 'i' } },
        { 'config.inputs.prompt': { $regex: q, $options: 'i' } }
      ]
    }).sort({ createdAt: -1 });

    res.json({
      query: q,
      total: jobs.length,
      results: jobs.map(job => ({
        jobId: job.jobId,
        type: job.type,
        name: job.config.loraName || job.sourceVideo?.filename || job.jobId,
        createdAt: job.createdAt
      }))
    });

  } catch (error) {
    console.error('Error searching assets:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/assets/stats:
 *   get:
 *     summary: Get usage statistics for a user
 *     description: Returns counts and storage usage across all asset types
 *     tags: [Assets]
 *     parameters:
 *       - in: query
 *         name: userId
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Usage statistics
 */
router.get('/stats', async (req, res) => {
  try {
    const { userId } = req.query;

    if (!userId) {
      return res.status(400).json({ error: 'userId is required' });
    }

    const jobs = await Job.find({ userId, status: 'completed' });

    const stats = {
      totalJobs: jobs.length,
      byType: {
        'lora-training': jobs.filter(j => j.type === 'lora-training').length,
        'image-generation': jobs.filter(j => j.type === 'image-generation').length,
        'transcription': jobs.filter(j => j.type === 'transcription').length
      },
      totalStorageBytes: jobs.reduce((sum, j) => sum + (j.usage?.storageBytes || 0), 0),
      oldestAsset: jobs.length > 0 ? jobs.sort((a, b) => a.createdAt - b.createdAt)[0].createdAt : null,
      newestAsset: jobs.length > 0 ? jobs.sort((a, b) => b.createdAt - a.createdAt)[0].createdAt : null
    };

    stats.totalStorageGB = (stats.totalStorageBytes / 1024 / 1024 / 1024).toFixed(2);
    stats.estimatedMonthlyCost = (stats.totalStorageBytes / 1024 / 1024 / 1024 * 0.023).toFixed(2);

    res.json(stats);

  } catch (error) {
    console.error('Error getting stats:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
