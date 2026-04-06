# LAB 3: Database Fundamentals Integration

This lab brings together PostgreSQL, Redis, and MongoDB to build a student dashboard and support a forum-style discussion feature.
It also includes a dedicated test suite so each piece of the workflow can be validated in isolation.

## What Is In This Lab

- `db-connection.py`: creates and manages the PostgreSQL connection pool.
- `redis-cache.py`: caches course progress in Redis and falls back to PostgreSQL when needed.
- `mongo-integrator.py`: stores and reads forum threads and replies in MongoDB.
- `dashboard.py`: combines PostgreSQL, Redis, and MongoDB data into one student dashboard response.
- `test_lab3.py`: consolidated tests for the dashboard, cache, and MongoDB integration code.

## What The Modules Do

### `db-connection.py`
This module loads PostgreSQL settings from the environment, creates a connection pool, and exposes helpers to get and release connections safely.

### `redis-cache.py`
This module calculates a student’s course progress, stores the result in Redis, and reuses cached values when possible.
It also supports cache invalidation when lesson progress changes.

### `mongo-integrator.py`
This module manages the forum data used by the course dashboard.
It can create threads, add replies, search threads, fetch threads for a course, and count thread activity per course.

### `dashboard.py`
This module combines the data from all three systems.
It builds a student dashboard that includes enrolled courses, progress percentage, last lesson activity, and forum thread counts.
It also exposes a helper that shows the time between lesson completions.

### `test_lab3.py`
This file contains the full LAB 3 test suite.
It covers the main success paths and the important edge cases for dashboard assembly, Redis caching, and MongoDB operations.

## Environment Variables

Add the following values to your `.env` file:

```env
# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CACHE_TTL_SECONDS=300

# MongoDB
MONGO_URI=mongodb://localhost:27017/
MONGO_DATABASE=learning_platform
MONGO_THREADS_COLLECTION=forum_threads

# Demo settings
DASHBOARD_DEMO_STUDENT_ID=1
```

## Requirements

- Python 3.10+
- PostgreSQL
- Redis
- MongoDB
- `pytest`
- `python-dotenv`
- `psycopg2`
- `redis`
- `pymongo`

## Running The Lab

From the project root:

```powershell
poetry run python -m amalitech_training.database_fundamentals.LAB_3.dashboard
```

If you want to run the individual modules directly from the lab folder, make sure the environment is configured first.

## Running The Tests

```powershell
poetry run pytest amalitech_training/database_fundamentals/LAB_3/test_lab3.py -q
```

Current test status:

- `18 passed`

## Notes

- The implementation files no longer contain inline demo test blocks.
- All tests are now kept in `test_lab3.py`.
- The MongoDB module still uses `datetime.utcnow()` in a few places, which currently raises deprecation warnings during tests. The suite passes, but that can be updated in a follow-up.
