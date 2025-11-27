/**
 * Webhook notification utilities
 * Handles calling client webhooks with retry logic
 */

const MAX_WEBHOOK_ATTEMPTS = 3;
const WEBHOOK_TIMEOUT = 10000; // 10 seconds

/**
 * Send webhook notification with retry logic
 */
export async function sendWebhook(webhookUrl, payload, retryCount = 0) {
  if (!webhookUrl) {
    return { success: false, error: 'No webhook URL provided' };
  }

  try {
    console.log(`📞 Calling webhook (attempt ${retryCount + 1}/${MAX_WEBHOOK_ATTEMPTS}): ${webhookUrl}`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), WEBHOOK_TIMEOUT);

    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'ContentGenerationService/1.0'
      },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Webhook returned ${response.status}: ${response.statusText}`);
    }

    console.log(`   ✅ Webhook successful`);

    return {
      success: true,
      statusCode: response.status,
      attempts: retryCount + 1
    };

  } catch (error) {
    console.error(`   ❌ Webhook failed (attempt ${retryCount + 1}):`, error.message);

    // Retry with exponential backoff
    if (retryCount < MAX_WEBHOOK_ATTEMPTS - 1) {
      const delay = Math.pow(2, retryCount) * 1000; // 1s, 2s, 4s
      console.log(`   🔄 Retrying in ${delay}ms...`);

      await new Promise(resolve => setTimeout(resolve, delay));
      return sendWebhook(webhookUrl, payload, retryCount + 1);
    }

    return {
      success: false,
      error: error.message,
      attempts: retryCount + 1
    };
  }
}

/**
 * Create webhook payload for job completion
 */
export function createJobCompletePayload(job) {
  const payload = {
    event: 'job.completed',
    jobId: job.jobId,
    userId: job.userId,
    type: job.type,
    status: job.status,
    completedAt: job.completedAt,
    createdAt: job.createdAt
  };

  // Add type-specific data
  if (job.type === 'lora-training' && job.versions.length > 0) {
    const latestVersion = job.versions[job.versions.length - 1];
    payload.lora = {
      modelUrl: latestVersion.modelUrl,
      version: latestVersion.version,
      trigger: job.config.trigger
    };
  }

  if (job.type === 'image-generation' && job.versions.length > 0) {
    payload.images = job.versions[0].images || [];
  }

  return payload;
}

/**
 * Create webhook payload for job failure
 */
export function createJobFailedPayload(job) {
  return {
    event: 'job.failed',
    jobId: job.jobId,
    userId: job.userId,
    type: job.type,
    status: 'failed',
    error: job.error,
    failedAt: new Date().toISOString()
  };
}
