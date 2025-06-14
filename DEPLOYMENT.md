# Vercel Deployment Guide

## Prerequisites
- Vercel account (free at vercel.com)
- Vercel CLI installed: `npm i -g vercel`
- GEMINI_API_KEY from Google AI Studio

## Deployment Steps

### 1. Deploy Backend API

```bash
cd backend

# Use the minimal requirements for deployment
cp requirements-deploy.txt requirements.txt

# Deploy to Vercel
vercel

# Follow prompts:
# - Link to existing project or create new
# - Choose Python as framework
# - Keep default settings
```

### 2. Set Backend Environment Variables

In Vercel dashboard for your backend:
- Go to Settings > Environment Variables
- Add:
  - `GEMINI_API_KEY`: Your Google Gemini API key
  - `SECRET_KEY`: Generate a secure random string
  - `DATABASE_URL`: sqlite+aiosqlite:///./relevia.db (or use Vercel Postgres)

### 3. Deploy Frontend

```bash
cd ../frontend

# Update the API URL in your .env.local
echo "NEXT_PUBLIC_API_URL=https://your-backend.vercel.app/api/v1" > .env.local

# Deploy to Vercel
vercel

# Follow prompts:
# - Link to existing project or create new
# - Framework preset: Next.js
# - Keep default settings
```

### 4. Test Your Deployment

1. Visit your frontend URL
2. Navigate to `/auth` to register/login
3. Start using the learning platform!

## Important Notes

- The backend uses SQLite by default (file-based)
- For production, consider using Vercel Postgres or another hosted database
- Auth tokens expire after 30 minutes (configurable in settings)
- All API routes require authentication except `/api/auth/*` and `/api/health`

## Troubleshooting

### Backend not deploying?
- Check that `api/index.py` exists and imports your FastAPI app
- Ensure all dependencies in requirements.txt are compatible with Vercel

### Frontend can't connect to backend?
- Verify NEXT_PUBLIC_API_URL is set correctly
- Check CORS settings in backend allow your frontend domain

### Database issues?
- SQLite works for MVP but has limitations on Vercel
- Consider switching to Vercel Postgres for production