/**
 * AssemblyAI client wrapper
 * Handles audio/video transcription
 */

import fs from 'fs';
import { Readable } from 'stream';

const ASSEMBLYAI_BASE_URL = 'https://api.assemblyai.com/v2';

export class AssemblyAIClient {
  constructor(apiKey) {
    if (!apiKey) {
      throw new Error('ASSEMBLYAI_API_KEY is required');
    }
    this.apiKey = apiKey;
    this.headers = {
      'authorization': apiKey,
      'content-type': 'application/json'
    };
  }

  /**
   * Upload audio file to AssemblyAI
   * Only needed for local files - can skip if you have a public S3 URL
   */
  async uploadFile(filePath) {
    try {
      const fileStream = fs.createReadStream(filePath);
      const stats = fs.statSync(filePath);

      const response = await fetch(`${ASSEMBLYAI_BASE_URL}/upload`, {
        method: 'POST',
        headers: {
          'authorization': this.apiKey,
          'content-type': 'application/octet-stream'
        },
        body: fileStream,
        duplex: 'half'
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      return data.upload_url;

    } catch (error) {
      console.error('AssemblyAI upload error:', error);
      throw error;
    }
  }

  /**
   * Upload from URL or Buffer
   */
  async uploadFromBuffer(buffer) {
    try {
      const response = await fetch(`${ASSEMBLYAI_BASE_URL}/upload`, {
        method: 'POST',
        headers: {
          'authorization': this.apiKey,
          'content-type': 'application/octet-stream'
        },
        body: buffer
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();
      return data.upload_url;

    } catch (error) {
      console.error('AssemblyAI upload error:', error);
      throw error;
    }
  }

  /**
   * Start transcription
   * @param {string} audioUrl - Publicly accessible URL (S3 or AssemblyAI upload URL)
   * @param {object} options - Transcription options
   * @returns {Promise<object>} - Transcription job with ID
   */
  async startTranscription(audioUrl, options = {}) {
    try {
      const requestBody = {
        audio_url: audioUrl,
        ...options
      };

      const response = await fetch(`${ASSEMBLYAI_BASE_URL}/transcript`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(`Transcription failed: ${error.error || response.statusText}`);
      }

      const data = await response.json();
      return data;

    } catch (error) {
      console.error('AssemblyAI transcription error:', error);
      throw error;
    }
  }

  /**
   * Get transcription status
   * Poll this until status is 'completed' or 'error'
   */
  async getTranscription(transcriptId) {
    try {
      const response = await fetch(`${ASSEMBLYAI_BASE_URL}/transcript/${transcriptId}`, {
        headers: this.headers
      });

      if (!response.ok) {
        throw new Error(`Get transcription failed: ${response.statusText}`);
      }

      const data = await response.json();
      return data;

    } catch (error) {
      console.error('AssemblyAI get transcription error:', error);
      throw error;
    }
  }

  /**
   * Wait for transcription to complete
   * Polls every 3 seconds (AssemblyAI recommended interval)
   */
  async waitForCompletion(transcriptId, onProgress = null) {
    while (true) {
      const transcript = await this.getTranscription(transcriptId);

      if (onProgress) {
        onProgress(transcript);
      }

      if (transcript.status === 'completed') {
        return transcript;
      }

      if (transcript.status === 'error') {
        throw new Error(`Transcription failed: ${transcript.error}`);
      }

      // Wait 3 seconds before polling again (AssemblyAI recommendation)
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  }

  /**
   * Convenience method: upload and transcribe in one call
   */
  async transcribeFile(filePath, options = {}) {
    const uploadUrl = await this.uploadFile(filePath);
    const transcriptJob = await this.startTranscription(uploadUrl, options);
    return await this.waitForCompletion(transcriptJob.id);
  }

  /**
   * Transcribe from public URL (S3, etc.)
   */
  async transcribeUrl(audioUrl, options = {}) {
    const transcriptJob = await this.startTranscription(audioUrl, options);
    return await this.waitForCompletion(transcriptJob.id);
  }
}

export default AssemblyAIClient;
