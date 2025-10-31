# PostgreSQL Setup Guide

This guide will help you migrate from SQLite to PostgreSQL for production use.

## Why PostgreSQL?

PostgreSQL offers several advantages over SQLite for production financial applications:

- **Concurrency**: Multiple users can write simultaneously
- **ACID Compliance**: Better data integrity guarantees
- **Performance**: Handles large datasets efficiently
- **Features**: JSON support, full-text search, advanced indexing
- **Scalability**: Ready for production workloads

## Quick Setup

**🚀 Fastest way:** Use our automated setup script:
```bash
./setup_postgres_quick.sh
```

This script will:
- Check if PostgreSQL is installed and running
- Create database and user
- Set up permissions and extensions
- Configure your `.env` file
- Test the connection

For manual setup, continue below:

### 1. Install PostgreSQL

**macOS:**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Docker:**
```bash
docker run --name runway-postgres \
  -e POSTGRES_PASSWORD=runway_password \
  -e POSTGRES_USER=runway_user \
  -e POSTGRES_DB=runway_finance \
  -p 5432:5432 \
  -v runway_db_data:/var/lib/postgresql/data \
  -d postgres:16-alpine
```

### 2. Create Database and User

**Option A: Using the SQL script:**
```bash
# Login as postgres user
sudo -u postgres psql

# Run the setup script
\i setup_postgres.sql

# Exit
\q
```

**Option B: Manual setup:**
```bash
# Login as postgres user
sudo -u postgres psql

# Create database
CREATE DATABASE runway_finance;

# Create user
CREATE USER runway_user WITH PASSWORD 'runway_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE runway_finance TO runway_user;

# Connect to database and grant schema privileges
\c runway_finance
GRANT ALL ON SCHEMA public TO runway_user;

# Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

# Exit
\q
```

### 3. Configure Application

Copy the example environment file and update it:
```bash
cp .env.example .env
```

Edit `.env` and update the database URL:
```bash
DATABASE_URL=postgresql://runway_user:runway_password@localhost:5432/runway_finance
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Initialize Database

The application will automatically create all tables on first run:
```bash
python3 reset_and_setup.py
```

Or simply start the backend:
```bash
python3 -m uvicorn api.main:app --reload
```

## Cloud PostgreSQL Options

### Neon (Recommended for Free Tier)

1. Sign up at [neon.tech](https://neon.tech)
2. Create a new project
3. Copy the connection string
4. Update your `.env`:
```bash
DATABASE_URL=postgresql://user:pass@ep-xxx.region.neon.tech:5432/database?sslmode=require
```

### Supabase

1. Sign up at [supabase.com](https://supabase.com)
2. Create a new project
3. Copy the connection string from Settings > Database
4. Update your `.env`

### Railway

1. Sign up at [railway.app](https://railway.app)
2. Create a new PostgreSQL service
3. Copy the connection string
4. Update your `.env`

### AWS RDS

1. Create an RDS PostgreSQL instance
2. Configure security groups
3. Get the endpoint URL
4. Update your `.env`

## Migration from SQLite

### Option 1: Fresh Start (Recommended)

If you're in development, simply use the new PostgreSQL database:
```bash
# This will create a fresh database
python3 reset_and_setup.py
```

### Option 2: Data Migration

If you have important data in SQLite, you can migrate it:

1. **Export from SQLite:**
```bash
# Install pgloader
brew install pgloader  # macOS
# or
sudo apt install pgloader  # Ubuntu

# Run migration
pgloader sqlite://data/finance.db postgresql://runway_user:runway_password@localhost:5432/runway_finance
```

2. **Or use Python script:**
```python
# TODO: Create migration script if needed
```

## Verification

Test your setup:
```bash
# Check connection
python3 -c "from storage.database import DatabaseManager; from config import Config; db = DatabaseManager(Config.DATABASE_URL); print('Connected!')"

# Start backend and check logs
python3 -m uvicorn api.main:app --reload
```

Look for:
```
✅ Initializing database: postgresql://...
✅ Database tables created successfully
```

## Security Best Practices

### 1. Use Strong Passwords
Change the default password in production:
```bash
# In psql
ALTER USER runway_user WITH PASSWORD 'strong_random_password';
```

### 2. SSL/TLS for Cloud
Always use SSL for cloud databases:
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### 3. Connection Pooling (Production)
For high-traffic production, use a connection pooler like PgBouncer:
```bash
# Add to requirements.txt
pgbouncer
```

### 4. Backup Strategy
Set up regular backups:
```bash
# Manual backup
pg_dump -U runway_user runway_finance > backup_$(date +%Y%m%d).sql

# Restore
psql -U runway_user runway_finance < backup_20250101.sql
```

## Performance Tuning

### 1. Create Indexes
```sql
-- Already handled by SQLAlchemy models, but you can add more

-- For frequent queries on transactions
CREATE INDEX idx_transactions_user_date ON transactions(user_id, date DESC);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_merchant ON transactions(merchant_canonical);

-- For fuzzy search on merchants
CREATE INDEX idx_merchants_name_trgm ON merchants(name) USING gin (name gin_trgm_ops);
```

### 2. Analyze and Vacuum
Run periodically:
```sql
ANALYZE;
VACUUM ANALYZE;
```

### 3. Connection Pooling
Update `storage/database.py` for production:
```python
engine = create_engine(
    database_url,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600,   # Recycle after 1 hour
)
```

## Troubleshooting

### Connection Errors

**"psql: FATAL: role 'runway_user' does not exist"**
```bash
# Create the user first
sudo -u postgres createuser runway_user
```

**"FATAL: password authentication failed"**
```bash
# Reset password
sudo -u postgres psql
ALTER USER runway_user WITH PASSWORD 'new_password';
```

**"could not connect to server"**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS
```

### Import Errors

**"No module named 'psycopg2'"**
```bash
pip install psycopg2-binary
```

**"Peer authentication failed"**
Edit `pg_hba.conf`:
```bash
# Local connections
local   all             all                                     peer
host    all             all             127.0.0.1/32            md5
```

## Next Steps

- [ ] Set up automated backups
- [ ] Configure monitoring (e.g., pg_stat_statements)
- [ ] Set up connection pooling for production
- [ ] Enable query logging for debugging
- [ ] Configure replication for high availability

## Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL Guide](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [pgloader Documentation](https://pgloader.readthedocs.io/)
- [PostgreSQL Performance Guide](https://wiki.postgresql.org/wiki/Performance_Optimization)

