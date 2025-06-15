# Relevia Backend Setup Guide

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd relevia/backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment setup**
   Create a `.env` file in the backend directory:
   ```env
   DATABASE_URL=sqlite+aiosqlite:///./relevia.db
   SECRET_KEY=your-secret-key-here
   GEMINI_API_KEY=  # Optional: for AI question generation
   ```

4. **Initialize the database**
   ```bash
   python scripts/init_database_comprehensive.py
   ```
   
   This will:
   - Create all necessary tables
   - Add a default user (user@example.com / password123)
   - Set up the initial AI topic
   - Fix any schema issues

5. **Run the server**
   ```bash
   uvicorn main:app --port 8001 --host 0.0.0.0 --reload
   ```

## Automatic Initialization

The backend now includes automatic database initialization on startup. If you start the server with an empty database, it will automatically:
- Create all tables
- Add default user and topic
- Set up necessary relationships

## Default Credentials

- **Email**: user@example.com
- **Password**: password123

## Troubleshooting

### Database Schema Issues
If you encounter "no such column" errors, run:
```bash
python scripts/init_database_comprehensive.py
```

### Timezone Errors
The initialization script automatically fixes timezone issues in the database.

### Permission Errors
Make sure the backend directory has write permissions for creating the SQLite database file.

## Development Tips

1. The database file is `relevia.db` in the backend directory
2. Logs are available in the console when running with `--reload`
3. The API is available at `http://localhost:8001`
4. API documentation is at `http://localhost:8001/docs`

## Database Reset

To completely reset the database:
```bash
rm relevia.db
python scripts/init_database_comprehensive.py
```