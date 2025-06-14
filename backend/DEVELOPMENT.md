# Development Setup Guide

## Database Setup for Local Development

You have three options for local development:

### Option 1: Use Supabase (Recommended)
This uses the same database as production, ensuring consistency.

1. Copy `.env.example` to `.env`
2. Set `DATABASE_URL` to your Supabase connection string:
   ```
   DATABASE_URL=postgresql://[user]:[password]@[host]:6543/postgres
   ```

### Option 2: Local PostgreSQL
For completely offline development:

1. Install PostgreSQL locally
2. Create a database:
   ```bash
   createdb relevia
   ```
3. Set in `.env`:
   ```
   DATABASE_URL=postgresql://localhost:5432/relevia
   ```

### Option 3: Docker PostgreSQL
Quick setup with Docker:

```bash
docker run --name relevia-postgres -e POSTGRES_DB=relevia -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15
```

Then in `.env`:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/relevia
```

## Initial Database Setup

After configuring your database:

1. **Create tables using Alembic**:
   ```bash
   alembic upgrade head
   ```

2. **Create a development user**:
   ```sql
   INSERT INTO users (email, username, hashed_password, is_active) VALUES
   ('dev@example.com', 'developer', '$2b$12$KvN3XmHhXiU8h7yYeqLWaOU./H0kKhJVmZfbQj9O3xlx7lAKfKYhq', true);
   ```
   This creates a user with password: `devpass123`

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```

## Best Practices

1. **Never use SQLite in production** - It's not suitable for concurrent access
2. **Use the same database type locally as in production** - Prevents SQL dialect issues
3. **Keep test data separate** - Use different emails for dev vs production
4. **Use environment variables** - Never hardcode credentials

## Troubleshooting

### "DATABASE_URL must be set" error
- Make sure you've created `.env` file with DATABASE_URL
- Check that `.env` is in the backend directory

### Connection refused
- Ensure PostgreSQL is running
- Check the connection string format
- Verify firewall/network settings

### Authentication issues
- Make sure you've inserted a test user
- Verify the password hash matches your input
- Check SECRET_KEY is set in .env