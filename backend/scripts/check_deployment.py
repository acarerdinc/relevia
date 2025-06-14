"""Check deployment configuration and database connection"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Settings

settings = Settings()

print("=== Deployment Configuration Check ===")
print(f"Running on Vercel: {os.environ.get('VERCEL', 'No')}")
print(f"DATABASE_URL: {settings.DATABASE_URL[:50]}..." if len(settings.DATABASE_URL) > 50 else f"DATABASE_URL: {settings.DATABASE_URL}")
print(f"SECRET_KEY: {'✓ Custom' if settings.SECRET_KEY != 'development-secret-key-change-in-production' else '✗ Default (INSECURE!)'}")
print(f"TURSO_DATABASE_URL: {'✓ Set' if os.environ.get('TURSO_DATABASE_URL') else '✗ Not set'}")
print(f"TURSO_AUTH_TOKEN: {'✓ Set' if os.environ.get('TURSO_AUTH_TOKEN') else '✗ Not set'}")

# If using SQLite, show warning
if 'sqlite' in settings.DATABASE_URL.lower():
    print("\n⚠️  WARNING: Using SQLite database!")
    print("SQLite databases on Vercel are temporary and will be reset on each deployment.")
    print("Please set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN environment variables.")
else:
    print("\n✓ Using persistent database (Turso)")