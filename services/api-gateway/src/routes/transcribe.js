import express from 'express';
import { v4 as uuidv4 } from 'uuid';
import Job from '../../../../shared/schemas/Job.js';
import { uploadFile } from '../../../../shared/storage/s3-client.js';
import AssemblyAIClient from '../providers/assemblyai-client.js';
import { sendWebhook } from '../../../../shared/utils/webhook.js';

const router = express.Router();

const assemblyAI = new AssemblyAIClient(process.env.ASSEMBLYAI_API_KEY);

/**
 * @swagger
 * /api/transcribe:
 *   post:
 *     summary: Transcribe audio or video file
 *     description: Upload and transcribe audio/video. Supports URLs or file uploads. Files are stored in S3, transcription via AssemblyAI.
 *     tags: [Transcription]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - userId
 *             properties:
 *               userId:
 *                 type: string
 *               audioUrl:
 *                 type: string
 *                 description: Public URL to audio/video file (or will upload to S3)
 *               fileName:
 *                 type: string
 *                 description: Original filename
 *               options:
 *                 type: object
 *                 properties:
 *                   speaker_labels:
 *                     type: boolean
 *                     description: Enable speaker diarization
 *                   auto_chapters:
 *                     type: boolean
 *                     description: Auto-generate chapters
 *                   sentiment_analysis:
 *                     type: boolean
 *                     description: Analyze sentiment
 *               webhookUrl:
 *                 type: string
 *                 description: Optional webhook to call when complete
 *     responses:
 *       201:
 *         description: Transcription job created
 *       400:
 *         description: Invalid request
 */
router.post('/', async (req, res) => {
  try {
    const {
      userId,
      audioUrl,
      fileName,
      options = {},
      webhookUrl
    } = req.body;

    if (!userId) {
      return res.status(400).json({ error: 'userId is required' });
    }

    if (!audioUrl) {
      return res.status(400).json({ error: 'audioUrl is required' });
    }

    // Create job in MongoDB
    const jobId = uuidv4();
    const job = new Job({
      jobId,
      userId,
      type: 'transcription',
      sourceVideo: {
        url: audioUrl,
        filename: fileName || audioUrl.split('/').pop()
      },
      config: {
        options,
        fileName
      },
      webhookUrl,
      status: 'processing',
      progress: 0
    });

    await job.save();

    console.log(`🎙️  Starting transcription for job ${jobId}`);
    console.log(`   Audio URL: ${audioUrl}`);

    // Start transcription in background
    processTranscription(jobId, userId, audioUrl, options, webhookUrl)
      .catch(error => {
        console.error(`Transcription failed for job ${jobId}:`, error);
      });

    res.status(201).json({
      jobId,
      status: 'processing',
      message: 'Transcription started'
    });

  } catch (error) {
    console.error('Error creating transcription job:', error);
    res.status(500).json({
      error: 'Failed to create transcription job',
      details: error.message
    });
  }
});

/**
 * Background task to process transcription
 */
async function processTranscription(jobId, userId, audioUrl, options, webhookUrl) {
  try {
    // Update status
    await Job.updateOne(
      { jobId },
      {
        $set: {
          progress: 10,
          startedAt: new Date()
        }
      }
    );

    console.log(`🎙️  Submitting to AssemblyAI...`);

    // Start transcription with AssemblyAI
    const transcriptJob = await assemblyAI.startTranscription(audioUrl, options);
    const transcriptId = transcriptJob.id;

    console.log(`   AssemblyAI transcript ID: ${transcriptId}`);

    // Store AssemblyAI ID for reference
    await Job.updateOne(
      { jobId },
      {
        $set: {
          'config.assemblyAIId': transcriptId,
          progress: 25
        }
      }
    );

    // Wait for completion with progress updates
    const finalTranscript = await assemblyAI.waitForCompletion(
      transcriptId,
      async (transcript) => {
        // Update progress based on AssemblyAI status
        let progress = 25;
        if (transcript.status === 'queued') progress = 25;
        if (transcript.status === 'processing') progress = 50;

        await Job.updateOne(
          { jobId },
          { $set: { progress } }
        );

        console.log(`   Transcription ${transcript.status}... (${progress}%)`);
      }
    );

    console.log(`   ✅ Transcription complete`);

    // Upload transcript to our S3
    const transcriptJson = JSON.stringify(finalTranscript, null, 2);
    const s3Key = `transcripts/${userId}/${jobId}/transcript.json`;
    const transcriptUrl = await uploadFile(
      s3Key,
      Buffer.from(transcriptJson),
      'application/json'
    );

    // Also save just the text
    const textS3Key = `transcripts/${userId}/${jobId}/transcript.txt`;
    const textUrl = await uploadFile(
      textS3Key,
      Buffer.from(finalTranscript.text),
      'text/plain'
    );

    console.log(`   ☁️  Uploaded to S3`);

    // Update job with results
    await Job.updateOne(
      { jobId },
      {
        $set: {
          status: 'completed',
          progress: 100,
          completedAt: new Date(),
          'usage.lastUsed': new Date()
        },
        $push: {
          versions: {
            version: 1,
            transcriptUrl,
            textUrl,
            s3Key,
            wordCount: finalTranscript.words?.length || 0,
            duration: finalTranscript.audio_duration,
            createdAt: new Date(),
            config: options
          }
        }
      }
    );

    console.log(`🎉 Transcription job ${jobId} completed!`);

    // Send webhook if configured
    if (webhookUrl) {
      console.log(`📞 Sending completion webhook...`);

      const webhookPayload = {
        event: 'job.completed',
        jobId,
        userId,
        type: 'transcription',
        status: 'completed',
        completedAt: new Date().toISOString(),
        timestamp: new Date().toISOString(),
        transcription: {
          transcriptUrl,
          textUrl,
          text: finalTranscript.text,
          wordCount: finalTranscript.words?.length || 0,
          duration: finalTranscript.audio_duration
        }
      };

      const webhookResult = await sendWebhook(webhookUrl, webhookPayload);

      await Job.updateOne(
        { jobId },
        {
          $set: {
            webhookAttempts: webhookResult.attempts || 0,
            webhookLastError: webhookResult.error || null
          }
        }
      );
    }

  } catch (error) {
    console.error(`❌ Transcription failed for job ${jobId}:`, error);

    // Update job as failed
    await Job.updateOne(
      { jobId },
      {
        $set: {
          status: 'failed',
          error: error.message
        }
      }
    );

    // Send failure webhook if configured
    if (webhookUrl) {
      await sendWebhook(webhookUrl, {
        event: 'job.failed',
        jobId,
        userId,
        type: 'transcription',
        status: 'failed',
        error: error.message,
        failedAt: new Date().toISOString(),
        timestamp: new Date().toISOString()
      });
    }
  }
}

/**
 * @swagger
 * /api/transcribe/from-s3:
 *   post:
 *     summary: Transcribe file already in S3
 *     description: Start transcription for an audio/video file already stored in S3
 *     tags: [Transcription]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - userId
 *               - s3Url
 *             properties:
 *               userId:
 *                 type: string
 *               s3Url:
 *                 type: string
 *                 description: S3 URL (must be publicly accessible or signed)
 *               webhookUrl:
 *                 type: string
 *     responses:
 *       201:
 *         description: Transcription started
 */
router.post('/from-s3', async (req, res) => {
  try {
    const { userId, s3Url, options = {}, webhookUrl } = req.body;

    if (!userId || !s3Url) {
      return res.status(400).json({ error: 'userId and s3Url are required' });
    }

    // Use the main transcription flow
    req.body.audioUrl = s3Url;
    req.body.fileName = s3Url.split('/').pop();

    // Forward to main handler
    return router.handle(
      { ...req, method: 'POST', url: '/', body: req.body },
      res
    );

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
