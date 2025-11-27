module.exports = {
  apps: [
    {
      name: 'content-api-gateway',
      script: './services/api-gateway/src/index.js',
      cwd: '/var/www/content-generation-service',
      instances: 1,
      exec_mode: 'fork',
      env: {
        NODE_ENV: 'production',
        API_GATEWAY_PORT: 5000
      },
      error_file: './logs/api-gateway-error.log',
      out_file: './logs/api-gateway-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M'
    },
    {
      name: 'lora-training-worker',
      script: './services/lora-training/start.sh',
      cwd: '/var/www/content-generation-service',
      instances: 1,
      exec_mode: 'fork',
      interpreter: 'bash',
      env: {
        LORA_TRAINING_PORT: 5001
      },
      error_file: './logs/lora-worker-error.log',
      out_file: './logs/lora-worker-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    }
  ]
};
