import express from 'express';
import Job from '../../../../shared/schemas/Job.js';

const router = express.Router();

/**
 * @swagger
 * /api/stream/job/{jobId}:
 *   get:
 *     summary: Stream real-time job progress updates
 *     description: Server-Sent Events (SSE) endpoint for real-time progress tracking. Sends updates every second until job completes.
 *     tags: [Streaming]
 *     parameters:
 *       - in: path
 *         name: jobId
 *         required: true
 *         schema:
 *           type: string
 *         description: Job ID to monitor
 *     responses:
 *       200:
 *         description: SSE stream
 *         content:
 *           text/event-stream:
 *             schema:
 *               type: string
 *       404:
 *         description: Job not found
 */
router.get('/job/:jobId', async (req, res) => {
  const { jobId } = req.params;

  // Check if job exists
  const job = await Job.findOne({ jobId });
  if (!job) {
    return res.status(404).json({ error: 'Job not found' });
  }

  // Set SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*'); // CORS for browsers

  console.log(`📡 SSE client connected for job ${jobId}`);

  // Send initial connection confirmation
  res.write(`data: ${JSON.stringify({ event: 'connected', jobId })}\n\n`);

  // Poll database and send updates
  const intervalId = setInterval(async () => {
    try {
      const currentJob = await Job.findOne({ jobId });

      if (!currentJob) {
        res.write(`data: ${JSON.stringify({ event: 'error', message: 'Job not found' })}\n\n`);
        clearInterval(intervalId);
        res.end();
        return;
      }

      // Send progress update
      const update = {
        event: 'progress',
        jobId: currentJob.jobId,
        status: currentJob.status,
        progress: currentJob.progress,
        type: currentJob.type,
        timestamp: new Date().toISOString()
      };

      // Add completion data if done
      if (currentJob.status === 'completed') {
        if (currentJob.type === 'lora-training' && currentJob.versions.length > 0) {
          const latestVersion = currentJob.versions[currentJob.versions.length - 1];
          update.lora = {
            modelUrl: latestVersion.modelUrl,
            version: latestVersion.version
          };
        }

        if (currentJob.type === 'image-generation' && currentJob.versions.length > 0) {
          update.images = currentJob.versions[0].images || [];
        }

        update.event = 'completed';
      }

      // Add error if failed
      if (currentJob.status === 'failed') {
        update.event = 'failed';
        update.error = currentJob.error;
      }

      res.write(`data: ${JSON.stringify(update)}\n\n`);

      // Close stream if job is done
      if (currentJob.status === 'completed' || currentJob.status === 'failed') {
        console.log(`📡 SSE stream ended for job ${jobId} (${currentJob.status})`);
        clearInterval(intervalId);
        res.end();
      }

    } catch (error) {
      console.error('SSE error:', error);
      res.write(`data: ${JSON.stringify({ event: 'error', message: error.message })}\n\n`);
      clearInterval(intervalId);
      res.end();
    }
  }, 1000); // Update every second

  // Cleanup on client disconnect
  req.on('close', () => {
    console.log(`📡 SSE client disconnected for job ${jobId}`);
    clearInterval(intervalId);
  });
});

export default router;
