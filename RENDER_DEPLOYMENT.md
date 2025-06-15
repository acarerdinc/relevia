# Render Deployment Guide

## Why Render?
- **Free tier** with 750 hours/month
- **Exportable logs** - Copy, download, or stream
- **Built-in PostgreSQL** - Free 90-day database
- **Zero cold starts** - Unlike Vercel
- **Better error messages** - Clear, detailed logs

## Quick Start

1. **Sign up**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `relevia` repo

3. **Configure Service**
   - **Name**: relevia-backend
   - **Root Directory**: backend
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

4. **Add Environment Variables**
   ```
   SECRET_KEY=<click-generate>
   FRONTEND_URL=https://your-frontend.vercel.app
   ENVIRONMENT=production
   ```

5. **Add PostgreSQL**
   - In your service, go to "Environment"
   - Click "Add Database"
   - Select "PostgreSQL"
   - Render auto-injects DATABASE_URL

## Accessing Logs

### From Dashboard:
1. Go to your service
2. Click "Logs" tab
3. Use "Download" button or copy text

### From CLI:
```bash
# Install Render CLI
brew tap render-oss/render
brew install render

# Get logs
render logs --service relevia-backend --tail
```

### Log Export:
- Click "Download logs" for CSV export
- Use API for programmatic access
- Stream logs to external services

## Monitoring
- Real-time metrics dashboard
- Performance insights
- Error tracking
- Uptime monitoring

## Costs
- **Free tier**: 750 hours/month (enough for 1 service)
- **PostgreSQL**: Free for 90 days, then $7/month
- **Paid plan**: $7/month for zero downtime

## Troubleshooting

### View Detailed Logs:
```bash
# Last 1000 lines
render logs --service relevia-backend --tail 1000

# Live streaming
render logs --service relevia-backend --tail --follow
```

### Common Issues:
1. **Module not found**: Check requirements.txt
2. **Port binding**: Render sets PORT automatically
3. **Database**: Check DATABASE_URL is injected
4. **Timeouts**: Increase workers in gunicorn command