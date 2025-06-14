# Database Management Guide

This guide explains how to manage database schema changes and initialization for Relevia.

## Setup

We use Alembic for database migrations to handle schema changes safely.

### First Time Setup

1. **Set your database URL** in environment variables:
   ```bash
   export POSTGRES_URL="your-supabase-connection-string"
   ```

2. **Initialize the database**:
   ```bash
   python scripts/manage_db.py init
   ```
   This will:
   - Run all migrations to create/update tables
   - Insert test users if they don't exist

## Managing Schema Changes

### When you modify models in `db/models.py`:

1. **Create a migration**:
   ```bash
   python scripts/manage_db.py create-migration -m "Add new field to users table"
   ```

2. **Review the migration** in `alembic/versions/`

3. **Apply the migration**:
   ```bash
   python scripts/manage_db.py migrate
   ```

### For production (Vercel):

1. Commit your migration files to git
2. Run migrations locally against production database:
   ```bash
   export POSTGRES_URL="production-supabase-url"
   python scripts/manage_db.py migrate
   ```

## Available Commands

### `python scripts/manage_db.py init`
- Creates all tables from scratch (or runs migrations)
- Inserts test users
- Safe to run multiple times

### `python scripts/manage_db.py migrate`
- Runs pending Alembic migrations
- Updates schema to latest version

### `python scripts/manage_db.py create-migration -m "message"`
- Creates a new migration file
- Automatically detects model changes

### `python scripts/manage_db.py add-users`
- Only inserts test users
- Skips if users already exist

### `python scripts/manage_db.py reset`
- ⚠️ DANGEROUS: Drops all tables and recreates them
- Only for development!

## Test Users

The following users are created automatically:
- info@acarerdinc.com / fenapass1
- ogulcancelik@gmail.com / ordekzeze1
- begumcitamak@gmail.com / zazapass1

## Troubleshooting

### "Table already exists" error
- The database already has tables
- Use `migrate` instead of `init`

### "No such table" error
- Run `python scripts/manage_db.py init`

### Schema out of sync
1. Create a migration: `python scripts/manage_db.py create-migration -m "fix schema"`
2. Review and edit the migration if needed
3. Apply it: `python scripts/manage_db.py migrate`

## For Vercel Deployment

Since Vercel is serverless, you can't run migrations on the server. Instead:

1. **Option 1**: Run migrations locally
   ```bash
   export POSTGRES_URL="your-production-db-url"
   python scripts/manage_db.py migrate
   ```

2. **Option 2**: Use the temporary endpoint (if enabled)
   ```
   POST https://your-app.vercel.app/api/v1/setup/init-database-setup-2024
   ```
   Remember to set `INIT_TOKEN=init-relevia-2024-secure` in Vercel env vars

3. **Option 3**: Use Supabase SQL Editor
   - Run the SQL from `scripts/insert_users.sql`