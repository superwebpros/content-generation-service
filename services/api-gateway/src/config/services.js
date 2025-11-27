/**
 * Configuration for internal service URLs
 */

export const SERVICES = {
  LORA_TRAINING: {
    baseUrl: process.env.LORA_TRAINING_URL || 'http://localhost:5001',
    endpoints: {
      train: '/train',
      health: '/health'
    }
  }
};

/**
 * Call the LoRA training service
 */
export async function triggerTrainingWorker(jobId, trainingData) {
  try {
    const response = await fetch(`${SERVICES.LORA_TRAINING.baseUrl}/train`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        job_id: jobId,
        user_id: trainingData.userId,
        video_url: trainingData.videoUrl,
        lora_name: trainingData.loraName,
        trigger: trainingData.trigger,
        steps: trainingData.steps,
        learning_rate: trainingData.learning_rate
      })
    });

    if (!response.ok) {
      throw new Error(`Training service returned ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error calling training service:', error);
    throw error;
  }
}
