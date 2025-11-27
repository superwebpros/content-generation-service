import mongoose from 'mongoose';

const { Schema } = mongoose;

const jobVersionSchema = new Schema({
  version: { type: Number, required: true },
  modelUrl: { type: String, required: true },
  s3Key: { type: String, required: true },
  sizeBytes: { type: Number },
  createdAt: { type: Date, default: Date.now },
  config: { type: Object }
}, { _id: false });

const jobSchema = new Schema({
  jobId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  userId: {
    type: String,
    required: true,
    index: true
  },
  type: {
    type: String,
    required: true,
    enum: ['lora-training', 'image-generation', 'video-generation', 'transcription'],
    index: true
  },

  // Source inputs
  sourceVideo: {
    url: String,
    filename: String,
    sizeBytes: Number
  },

  // Configuration (flexible per job type)
  config: {
    type: Object,
    default: {}
  },

  // Webhook notification (optional)
  webhookUrl: {
    type: String,
    validate: {
      validator: function(v) {
        if (!v) return true; // Optional field
        return /^https?:\/\/.+/.test(v);
      },
      message: 'webhookUrl must be a valid HTTP/HTTPS URL'
    }
  },
  webhookAttempts: {
    type: Number,
    default: 0
  },
  webhookLastError: String,

  // Outputs (versioned for LoRA training)
  versions: [jobVersionSchema],

  // Job state
  status: {
    type: String,
    required: true,
    enum: ['queued', 'processing', 'completed', 'failed'],
    default: 'queued',
    index: true
  },
  progress: {
    type: Number,
    default: 0,
    min: 0,
    max: 100
  },
  error: String,

  // Usage tracking
  usage: {
    storageBytes: { type: Number, default: 0 },
    apiCalls: { type: Number, default: 0 },
    lastUsed: Date
  },

  // Timestamps
  createdAt: { type: Date, default: Date.now, index: true },
  startedAt: Date,
  completedAt: Date
}, {
  timestamps: true
});

// Indexes for common queries
jobSchema.index({ userId: 1, createdAt: -1 });
jobSchema.index({ status: 1, createdAt: -1 });
jobSchema.index({ 'usage.lastUsed': 1 });

export default mongoose.model('Job', jobSchema);
