# Database Connection Guide for Quiz Sessions

This guide explains how to use the new connection management system for handling database connections during quiz sessions on Vercel with Supabase.

## Overview

The connection management system provides:
- Automatic retry logic for transient connection failures
- Optimized configuration for Supabase/Supavisor pooler
- Batch processing for multiple database operations
- Health monitoring and connection statistics

## Key Components

### 1. Connection Manager (`db/connection_manager.py`)

The `ConnectionManager` class handles all database connections with built-in retry logic:

```python
from db.connection_manager import connection_manager, with_retry

# Get a session with retry logic
async with connection_manager.get_session() as db:
    # Your database operations here
    pass

# Or use the decorator
@with_retry(timeout=10.0)
async def my_endpoint(db: AsyncSession = None):
    # Database operations
    pass
```

### 2. Batch Processor (`services/batch_processor.py`)

For quiz sessions with multiple database operations:

```python
from services.batch_processor import batch_processor, BatchContext

# Use context manager for batch operations
async with BatchContext() as batch:
    # Add operations to batch
    await batch.add_operation({
        'type': 'quiz_question',
        'data': {...}
    })
    # Operations are automatically flushed on exit

# Or manually control flushing
await batch_processor.add_operation(operation)
await batch_processor.flush()
```

## Usage Examples

### Quiz Endpoints with Retry

```python
@router.post("/start")
@with_retry(timeout=10.0)
async def start_quiz(request: StartQuizRequest, db: AsyncSession = None):
    """Start a new quiz session with automatic retry"""
    session = await quiz_engine.start_quiz_session(
        db=db,
        user_id=request.user_id,
        topic_id=request.topic_id
    )
    await db.commit()
    return {"session_id": session.id}
```

### Batch Processing Quiz Answers

```python
async def process_quiz_session(session_id: int, answers: List[Dict]):
    """Process multiple quiz answers efficiently"""
    async with BatchContext() as batch:
        for answer in answers:
            await batch.add_operation({
                'type': 'quiz_question',
                'data': {
                    'quiz_session_id': session_id,
                    'question_id': answer['question_id'],
                    'user_answer': answer['answer'],
                    'is_correct': answer['is_correct'],
                    'time_spent': answer['time_spent']
                }
            })
        # All operations are committed together
```

### Prefetching Quiz Data

```python
# Prefetch all necessary data for a quiz session
quiz_data = await batch_processor.prefetch_quiz_data(
    db=db,
    user_id=user_id,
    topic_ids=[1, 2, 3]
)
# Returns: topics, skills, interests, questions - all in one query
```

## Configuration

The system automatically detects the environment and optimizes accordingly:

- **Vercel + Supabase Pooler**: Uses `NullPool` with transaction-safe settings
- **Local Development**: Uses standard connection pooling

### Environment Variables

```bash
DATABASE_URL=postgresql://...  # Your database URL
VERCEL=1                       # Set automatically on Vercel
```

## Health Monitoring

Monitor database health with the health endpoints:

```bash
# Basic health check
GET /api/v1/health

# Database connection health
GET /api/v1/health/db

# Detailed system health
GET /api/v1/health/detailed
```

## Best Practices

1. **Use Retry Decorators**: Always use `@with_retry()` for database operations
2. **Batch Operations**: Group multiple operations together to reduce round trips
3. **Set Appropriate Timeouts**: 
   - Read operations: 5-10 seconds
   - Write operations: 10-15 seconds
   - Batch operations: 15-20 seconds
4. **Monitor Health**: Check `/health/db` endpoint regularly
5. **Handle Errors Gracefully**: The system will retry transient errors automatically

## Troubleshooting

### Common Issues

1. **DuplicatePreparedStatementError**
   - Already handled by UUID-based statement names
   - No action needed

2. **Connection Timeouts**
   - Check if using correct pooler URL (port 6543)
   - Verify Supavisor is enabled in Supabase dashboard

3. **Too Many Connections**
   - System uses `NullPool` to prevent this
   - If still occurring, check for connection leaks

### Connection Statistics

```python
# Get connection statistics
stats = connection_manager.get_stats()
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Total retries: {stats['retries']}")
```

## Migration Guide

To migrate existing endpoints:

1. Remove `Depends(get_db)` from function parameters
2. Add `@with_retry()` decorator
3. Add `db: AsyncSession = None` parameter
4. No other changes needed!

Before:
```python
async def my_endpoint(db: AsyncSession = Depends(get_db)):
    # code
```

After:
```python
@with_retry(timeout=10.0)
async def my_endpoint(db: AsyncSession = None):
    # code
```