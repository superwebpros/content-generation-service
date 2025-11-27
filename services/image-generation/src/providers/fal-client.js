/**
 * fal.ai client wrapper
 * Handles communication with fal.ai API
 */

import * as fal from '@fal-ai/client';
import fs from 'fs';
import { Blob } from 'buffer';

export class FalImageGenerator {
  constructor(apiKey) {
    if (!apiKey) {
      throw new Error('FAL_KEY is required');
    }

    fal.config({ credentials: apiKey });
    this.fal = fal;
  }

  /**
   * Upload an image to fal.ai storage
   * Accepts URL, file path, or Buffer
   */
  async uploadImage(source, contentType = 'image/jpeg') {
    try {
      let buffer;

      if (typeof source === 'string') {
        if (source.startsWith('http://') || source.startsWith('https://')) {
          // Download from URL
          const response = await fetch(source);
          const arrayBuffer = await response.arrayBuffer();
          buffer = Buffer.from(arrayBuffer);
        } else {
          // Read from file path
          buffer = fs.readFileSync(source);
        }
      } else if (Buffer.isBuffer(source)) {
        buffer = source;
      } else {
        throw new Error('Invalid image source: must be URL, file path, or Buffer');
      }

      const blob = new Blob([buffer], { type: contentType });
      const url = await this.fal.storage.upload(blob, { contentType });

      return url;

    } catch (error) {
      console.error('Error uploading to fal.ai:', error);
      throw error;
    }
  }

  /**
   * Generate images using fal.ai
   */
  async generate(endpoint, inputs, onProgress = null) {
    try {
      const result = await this.fal.subscribe(endpoint, {
        input: inputs,
        logs: true,
        onQueueUpdate: (update) => {
          if (update.status === 'IN_PROGRESS') {
            console.log('fal.ai generation in progress...');
            if (update.logs) {
              update.logs.forEach(log => console.log(`  ${log.message}`));
            }
          }

          if (onProgress) {
            onProgress(update);
          }
        }
      });

      return result;

    } catch (error) {
      console.error('fal.ai generation error:', error);
      throw error;
    }
  }

  /**
   * Download image from fal.ai result URL
   */
  async downloadImage(imageUrl) {
    try {
      const response = await fetch(imageUrl);
      if (!response.ok) {
        throw new Error(`Failed to download image: ${response.statusText}`);
      }

      return await response.arrayBuffer();

    } catch (error) {
      console.error('Error downloading image:', error);
      throw error;
    }
  }
}
