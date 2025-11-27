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
    }
    // LoRA training service will be added later
    // {
    //   name: 'lora-training-worker',
    //   script: 'services/lora-training/app.py',
    //   cwd: '/var/www/content-generation-service',
    //   interpreter: 'python3',
    //   instances: 1,
    //   exec_mode: 'fork',
    //   env: {
    //     LORA_TRAINING_PORT: 5001
    //   }
    // }
  ]
};
