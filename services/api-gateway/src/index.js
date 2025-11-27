import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import connectDB from './config/db.js';
import loraRoutes from './routes/lora.js';
import imageRoutes from './routes/images.js';
import jobsRoutes from './routes/jobs.js';
import streamRoutes from './routes/stream.js';
import transcribeRoutes from './routes/transcribe.js';
import assetsRoutes from './routes/assets.js';
import { specs, swaggerUi } from './config/swagger.js';

// ES modules workaround for __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables from root
dotenv.config({ path: path.join(__dirname, '../../../.env') });

const app = express();
const PORT = process.env.API_GATEWAY_PORT || 5000;

// Connect to MongoDB
await connectDB();

// Middleware
app.use(helmet()); // Security headers
app.use(cors()); // Enable CORS
app.use(morgan('combined')); // Logging
app.use(express.json()); // Parse JSON bodies
app.use(express.urlencoded({ extended: true })); // Parse URL-encoded bodies

// Swagger documentation
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs, {
  customSiteTitle: 'Content Generation API Docs',
  customCss: '.swagger-ui .topbar { display: none }'
}));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'content-generation-api-gateway',
    version: '1.0.0',
    timestamp: new Date().toISOString()
  });
});

// API Routes
app.use('/api/jobs', jobsRoutes); // General jobs endpoint (all types)
app.use('/api/lora', loraRoutes); // LoRA-specific endpoints
app.use('/api/images', imageRoutes); // Image generation endpoints
app.use('/api/transcribe', transcribeRoutes); // Audio/video transcription
app.use('/api/assets', assetsRoutes); // Asset browsing/retrieval
app.use('/api/stream', streamRoutes); // Server-Sent Events for real-time updates

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    path: req.path
  });
});

// Error handler
app.use((err, req, res, next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: 'Internal Server Error',
    message: err.message,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`✅ Content Generation API Gateway running on port ${PORT}`);
  console.log(`📍 Health check: http://localhost:${PORT}/health`);
  console.log(`🚀 API Base URL: http://localhost:${PORT}/api`);
  console.log(`📝 Environment: ${process.env.NODE_ENV || 'development'}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received. Shutting down gracefully...');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT received. Shutting down gracefully...');
  process.exit(0);
});
