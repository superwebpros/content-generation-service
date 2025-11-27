/**
 * Mock for AssemblyAI client
 * Prevents real API calls during testing
 */

export default class AssemblyAIClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }

  async uploadFile(filePath) {
    return 'https://mock-assemblyai.com/uploaded-audio.mp3';
  }

  async uploadFromBuffer(buffer) {
    return 'https://mock-assemblyai.com/uploaded-audio.mp3';
  }

  async startTranscription(audioUrl, options = {}) {
    return {
      id: 'mock-transcript-id-123',
      status: 'queued',
      audio_url: audioUrl
    };
  }

  async getTranscription(transcriptId) {
    return {
      id: transcriptId,
      status: 'completed',
      text: 'This is a mock transcript. In a real test, this would be the actual transcribed text from the audio file.',
      words: Array(50).fill({ text: 'word', start: 0, end: 1000 }),
      audio_duration: 30.5
    };
  }

  async waitForCompletion(transcriptId, onProgress = null) {
    // Simulate quick processing
    if (onProgress) {
      onProgress({ status: 'queued' });
      onProgress({ status: 'processing' });
    }

    return {
      id: transcriptId,
      status: 'completed',
      text: 'This is a mock transcript. The audio was successfully processed, but this is a simulated response for testing purposes. No actual API call was made to AssemblyAI, saving you API costs.',
      words: Array(50).fill({ text: 'word', start: 0, end: 1000 }),
      audio_duration: 30.5,
      confidence: 0.95
    };
  }

  async transcribeFile(filePath, options = {}) {
    return await this.waitForCompletion('mock-transcript-id');
  }

  async transcribeUrl(audioUrl, options = {}) {
    return await this.waitForCompletion('mock-transcript-id');
  }
}
