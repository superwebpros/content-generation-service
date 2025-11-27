import { S3Client, PutObjectCommand, GetObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import dotenv from 'dotenv';
import fs from 'fs';

dotenv.config();

const s3Client = new S3Client({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

const BUCKET = process.env.AWS_S3_BUCKET || 'content-generation-assets';

/**
 * Upload a file to S3
 * @param {string} key - S3 key (path)
 * @param {Buffer|Stream} body - File content
 * @param {string} contentType - MIME type
 * @returns {Promise<string>} - Public URL
 */
export async function uploadFile(key, body, contentType = 'application/octet-stream') {
  try {
    const command = new PutObjectCommand({
      Bucket: BUCKET,
      Key: key,
      Body: body,
      ContentType: contentType,
    });

    await s3Client.send(command);

    return `https://${BUCKET}.s3.amazonaws.com/${key}`;
  } catch (error) {
    console.error('S3 upload error:', error);
    throw error;
  }
}

/**
 * Upload a local file to S3
 * @param {string} filePath - Local file path
 * @param {string} key - S3 key (path)
 * @returns {Promise<string>} - Public URL
 */
export async function uploadLocalFile(filePath, key) {
  const fileStream = fs.createReadStream(filePath);
  const stats = fs.statSync(filePath);

  // Determine content type based on extension
  let contentType = 'application/octet-stream';
  if (filePath.endsWith('.safetensors')) {
    contentType = 'application/octet-stream';
  } else if (filePath.endsWith('.json')) {
    contentType = 'application/json';
  } else if (filePath.endsWith('.jpg') || filePath.endsWith('.jpeg')) {
    contentType = 'image/jpeg';
  } else if (filePath.endsWith('.png')) {
    contentType = 'image/png';
  }

  return uploadFile(key, fileStream, contentType);
}

/**
 * Get a signed URL for temporary access
 * @param {string} key - S3 key (path)
 * @param {number} expiresIn - Expiration in seconds (default: 1 hour)
 * @returns {Promise<string>} - Signed URL
 */
export async function getSignedDownloadUrl(key, expiresIn = 3600) {
  const command = new GetObjectCommand({
    Bucket: BUCKET,
    Key: key,
  });

  return await getSignedUrl(s3Client, command, { expiresIn });
}

/**
 * Check if a file exists in S3
 * @param {string} key - S3 key (path)
 * @returns {Promise<boolean>}
 */
export async function fileExists(key) {
  try {
    await s3Client.send(new HeadObjectCommand({
      Bucket: BUCKET,
      Key: key,
    }));
    return true;
  } catch (error) {
    if (error.name === 'NotFound') {
      return false;
    }
    throw error;
  }
}

/**
 * Generate S3 key paths for different asset types
 */
export const S3Paths = {
  lora: (userId, jobId, version) => `loras/${userId}/${jobId}/v${version}/model.safetensors`,
  loraConfig: (userId, jobId, version) => `loras/${userId}/${jobId}/v${version}/config.json`,
  dataset: (userId, jobId) => `datasets/${userId}/${jobId}/`,
  generatedImage: (userId, jobId, filename) => `generated-images/${userId}/${jobId}/${filename}`,
  temp: (jobId, filename) => `temp/${jobId}/${filename}`,
};

export default s3Client;
