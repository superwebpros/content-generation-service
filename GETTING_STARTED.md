# Getting Started - Content Generation Service

## ✅ What's Built and Running

### Services
- **API Gateway** (Node.js/Express) - Port 5000 ✅
- **LoRA Training Worker** (Python/FastAPI) - Port 5001 ✅

### Infrastructure
- **MongoDB**: Database `content-generation` on Digital Ocean
- **S3**: Bucket `content-generation-assets` with auto-cleanup
- **PM2**: Both services running and auto-restart enabled

### Documentation
- **Node API Swagger**: http://localhost:5000/api-docs
- **Python Worker Swagger**: http://localhost:5001/docs

### Tests
- **Node (Jest)**: Framework configured (tests pending)
- **Python (pytest)**: 5 tests passing ✅

## Quick Test

### 1. Check Services Health
```bash
# API Gateway
curl http://localhost:5000/health

# Python Worker
curl http://localhost:5001/health
```

### 2. Create a Training Job
```bash
curl -X POST http://localhost:5000/api/lora/train \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "demo-user",
    "videoUrl": "https://example.com/video.mp4",
    "loraName": "my_avatar",
    "trigger": "person",
    "steps": 2500
  }'
```

Response:
```json
{
  "jobId": "uuid-here",
  "status": "queued",
  "message": "Training job created successfully"
}
```

### 3. Check Job Status
```bash
curl http://localhost:5000/api/lora/status/{jobId}
```

### 4. List All Jobs
```bash
curl "http://localhost:5000/api/lora/list?userId=demo-user"
```

## Development Workflow

### TDD Approach

**For Node.js API:**
```bash
cd services/api-gateway

# Write test first
vim tests/integration/new-feature.test.js

# Run tests (they fail)
npm test

# Implement feature
vim src/routes/new-feature.js

# Run tests (they pass)
npm test
```

**For Python Worker:**
```bash
cd services/lora-training

# Write test first
vim test_new_feature.py

# Run tests (they fail)
source venv/bin/activate
pytest -v

# Implement feature
vim some_module.py

# Run tests (they pass)
pytest -v
```

## Swagger Documentation

### Viewing Docs

**API Gateway**: http://localhost:5000/api-docs
**Python Worker**: http://localhost:5001/docs

### Adding New Endpoints

**Node.js:**
```javascript
/**
 * @swagger
 * /api/your-endpoint:
 *   post:
 *     summary: Your endpoint description
 *     tags: [YourTag]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               field:
 *                 type: string
 *     responses:
 *       200:
 *         description: Success
 */
router.post('/your-endpoint', async (req, res) => {
  // implementation
});
```

**Python (FastAPI):**
```python
class YourRequest(BaseModel):
    """Request model"""
    field: str = Field(..., description="Field description")

@app.post("/your-endpoint", response_model=YourResponse, tags=["YourTag"])
async def your_endpoint(request: YourRequest):
    """
    Endpoint description here

    This will automatically appear in Swagger docs
    """
    return {"result": "success"}
```

FastAPI auto-generates Swagger from Pydantic models!

## Service Communication

Services communicate via HTTP:

```javascript
// In API Gateway (Node)
const response = await fetch('http://localhost:5001/train', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
});
```

## PM2 Management

```bash
# View all services
pm2 list

# View logs
pm2 logs content-api-gateway
pm2 logs lora-training-worker

# Restart services
pm2 restart content-api-gateway
pm2 restart lora-training-worker

# Save configuration
pm2 save
```

## Next Steps

### Immediate (Phase 2)
1. **Implement full training pipeline** in `services/lora-training/app.py`
   - Use existing code from `core/`, `providers/`, `utils/`
   - Add MongoDB updates for progress tracking
   - Upload results to S3

2. **Add fal.ai API key** to `.env`
   ```
   FAL_KEY=your_key_here
   ```

3. **Test with real video**
   ```bash
   curl -X POST http://localhost:5000/api/lora/train \
     -H "Content-Type: application/json" \
     -d '{
       "userId": "real-user",
       "videoUrl": "s3://your-bucket/real-video.mp4",
       "loraName": "real_avatar",
       "trigger": "jf",
       "steps": 2500
     }'
   ```

### DNS & Public Access
```bash
# 1. Set up DNS (Cloudflare or your provider)
# Point content.superwebpros.com to your server IP

# 2. Enable nginx
sudo ln -s /var/www/content-generation-service/config/nginx/content.superwebpros.com.conf \
  /etc/nginx/sites-enabled/

# 3. Test nginx config
sudo nginx -t

# 4. Reload nginx
sudo systemctl reload nginx

# 5. Get SSL certificate
sudo certbot --nginx -d content.superwebpros.com

# 6. Update nginx config to enable HTTPS block
```

### Add Image Generation
1. Move your fal.ai scripts to `services/image-generation/`
2. Create routes in API Gateway
3. Reuse S3 and MongoDB infrastructure

## Architecture Diagram

```
                ┌─────────────────────┐
                │   Nginx (future)    │
                │  content.swp.com    │
                └──────────┬──────────┘
                           │
                ┌──────────▼──────────┐
                │   API Gateway       │
                │   Node.js :5000     │
                │   ✅ Swagger docs    │
                │   ✅ Jest tests      │
                └──────┬──────────────┘
                       │
            ┌──────────┼──────────┐
            │          │          │
       ┌────▼───┐  ┌──▼────┐  ┌──▼──────┐
       │MongoDB │  │  S3   │  │ Python  │
       │(jobs)  │  │(files)│  │ Worker  │
       │        │  │       │  │  :5001  │
       └────────┘  └───────┘  │ FastAPI │
                              │ pytest  │
                              └─────────┘
```

## Troubleshooting

### Service won't start
```bash
pm2 logs {service-name} --lines 50
# Check for errors
```

### MongoDB connection issues
```bash
# Verify connection string in .env
# Check Digital Ocean firewall/IP whitelist
```

### Port conflicts
```bash
# Check what's using the port
netstat -tlnp | grep :5000

# Update PORT_REGISTRY.md
```

## Production Checklist

Before going live:
- [ ] Set `NODE_ENV=production` in PM2 config
- [ ] Add authentication middleware
- [ ] Set up rate limiting
- [ ] Configure monitoring/alerts
- [ ] Set up log rotation
- [ ] Add error reporting (Sentry, etc.)
- [ ] Document all API endpoints
- [ ] Create integration tests
- [ ] Load testing
- [ ] Backup strategy for MongoDB

## Resources

- API Documentation: `README.md`
- Setup Summary: `SETUP_COMPLETE.md`
- Port Registry: `/var/www/PORT_REGISTRY.md`
- This Guide: `GETTING_STARTED.md`
