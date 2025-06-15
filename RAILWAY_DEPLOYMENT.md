# Railway Deployment Guide

## Quick Start

1. **Sign up for Railway**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

2. **Create a new project**
   ```bash
   # Install Railway CLI (optional but recommended)
   npm install -g @railway/cli
   
   # Login
   railway login
   
   # Create project
   railway init
   ```

3. **Deploy from GitHub**
   - In Railway dashboard, click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `relevia` repository
   - Railway will auto-detect the configuration

4. **Add PostgreSQL**
   - In your Railway project, click "New"
   - Select "Database" → "Add PostgreSQL"
   - Railway will automatically inject `DATABASE_URL`

5. **Set Environment Variables**
   - Go to your service's Variables tab
   - Add these variables:
   ```
   SECRET_KEY=<generate-a-secure-key>
   FRONTEND_URL=https://your-frontend.vercel.app
   ENVIRONMENT=production
   DEBUG=False
   ```

6. **Deploy**
   - Railway will automatically deploy on push to main
   - Or manually trigger: `railway up`

## Configuration Files

The project includes:
- `railway.json` - Railway-specific configuration
- `nixpacks.toml` - Build configuration
- `Procfile` - Start command

## Monitoring

- Check logs: `railway logs`
- View metrics in Railway dashboard
- Health endpoint: `https://your-app.railway.app/api/v1/health`

## Costs

- Railway offers $5 free credits monthly
- Basic usage typically costs $5-10/month
- PostgreSQL included in pricing

## Troubleshooting

1. **Build failures**
   - Check Python version in nixpacks.toml
   - Ensure requirements.txt is up to date

2. **Database connection issues**
   - Railway auto-injects DATABASE_URL
   - No need to manually configure

3. **Port binding**
   - Railway sets PORT environment variable
   - Our config auto-detects this

## Next Steps

After deployment:
1. Update your frontend's API URL to the Railway URL
2. Test authentication flow
3. Monitor performance in Railway dashboard