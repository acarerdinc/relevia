# Deployment Checklist for Turso Database

## Current Status
- ✅ Turso database created and initialized with test users
- ✅ Environment variables set on Vercel (TURSO_DATABASE_URL, TURSO_AUTH_TOKEN)
- ✅ Requirements updated with Turso dependencies
- ✅ Database URL format fixed (sqlite+libsql:// prefix)
- ⏳ Waiting for deployment limit reset

## Test Users
1. info@acarerdinc.com / fenapass1
2. ogulcancelik@gmail.com / ordekzeze1
3. begumcitamak@gmail.com / zazapass1

## Pre-Deployment Verification
1. Local test works: `python scripts/test_turso_connection.py`
2. Requirements.txt contains:
   - sqlalchemy-libsql==0.1.0
   - libsql-client==0.3.1
   - NO asyncpg (PostgreSQL)

## Post-Deployment Verification
1. Check logs for "[CONFIG] Using Turso database: sqlite+libsql://..."
2. Test login at: https://relevia-backend.vercel.app/api/v1/auth/login
3. Use test credentials above

## If Issues Persist
1. Check if deployment is using Python 3.9 (as configured in vercel.json)
2. Verify environment variables are set for Production environment
3. Check build logs for successful installation of libsql packages
4. Run deployment check: `python scripts/check_deployment.py`

## Alternative Solutions (if needed)
1. Consider using sync SQLAlchemy instead of async
2. Try direct libsql connection without SQLAlchemy
3. Use Vercel Postgres (temporary database) as last resort