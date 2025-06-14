# Supabase Setup for Vercel Deployment

## 1. Set Environment Variables in Vercel

Go to your Vercel project settings and add these environment variables:

1. **POSTGRES_URL** - Your Supabase database connection string (pooled connection)
   - Get this from Supabase Dashboard > Settings > Database > Connection String > Connection Pooling
   - Should look like: `postgres://[user]:[password]@[host]:6543/postgres?pgbouncer=true`

2. **SECRET_KEY** - Your secure secret key for JWT
   - Already generated: `b2d8f3a9e7c1b5d4a0f6e8c2b7d9a3e5f8b1c4d7a2e5b8c3d6a9f2e5b8c1d4a7`

## 2. Initialize Database

After deployment, you need to initialize the database with tables and test users:

### Option A: Run locally with Vercel environment
```bash
cd backend
export POSTGRES_URL="your-supabase-connection-string"
python scripts/init_supabase.py
```

### Option B: Use Supabase SQL Editor
1. Go to Supabase Dashboard > SQL Editor
2. Run the table creation and user insertion SQL manually

## 3. Test Authentication

Once deployed and initialized, test with:
- Email: info@acarerdinc.com / Password: fenapass1
- Email: ogulcancelik@gmail.com / Password: ordekzeze1
- Email: begumcitamak@gmail.com / Password: zazapass1

## Troubleshooting

If authentication fails:
1. Check Vercel function logs for database connection errors
2. Verify POSTGRES_URL is set correctly in Vercel
3. Ensure database is initialized with test users
4. Check that you're using the pooled connection string (port 6543)