/**
 * Jest test setup
 * Automatically mocks external APIs to prevent costs
 */

// Force test environment
process.env.NODE_ENV = 'test';

// Mock fal.ai unless explicitly testing real APIs
if (process.env.REAL_API_TESTS !== 'true') {
  console.log('🧪 Using mocked APIs (costs: $0)');
  jest.mock('@fal-ai/client');
} else {
  console.warn('⚠️  Using REAL APIs - this will cost money!');
}

// Mock AssemblyAI unless explicitly testing
if (process.env.REAL_API_TESTS !== 'true') {
  // We'll create this mock
  jest.mock('../src/providers/assemblyai-client.js');
}

// Mock S3 uploads in tests (optional - you might want real S3 for integration tests)
if (process.env.MOCK_S3 === 'true') {
  jest.mock('../../../shared/storage/s3-client.js');
}
