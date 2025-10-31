#!/bin/bash
# Quick PostgreSQL Setup Script for Runway Finance
# This script automates the PostgreSQL setup process

set -e

echo "============================================================"
echo "Runway Finance: PostgreSQL Quick Setup"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    print_error "PostgreSQL is not installed!"
    echo ""
    echo "Please install PostgreSQL first:"
    echo "  macOS:   brew install postgresql@16"
    echo "  Ubuntu:  sudo apt install postgresql postgresql-contrib"
    echo "  Docker:  docker run --name runway-postgres -e POSTGRES_PASSWORD=runway_password -p 5432:5432 -d postgres:16-alpine"
    exit 1
fi

print_status "PostgreSQL is installed"

# Check if PostgreSQL is running
if ! pg_isready &> /dev/null; then
    print_warning "PostgreSQL is not running, attempting to start..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew services start postgresql@16 2>/dev/null || brew services start postgresql 2>/dev/null
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo systemctl start postgresql
    fi
    
    sleep 2
    
    if ! pg_isready &> /dev/null; then
        print_error "Could not start PostgreSQL. Please start it manually."
        exit 1
    fi
fi

print_status "PostgreSQL is running"

# Default database configuration
DB_NAME="runway_finance"
DB_USER="runway_user"
DB_PASSWORD="runway_password"

# Ask if user wants to customize
echo ""
read -p "Use default database settings? (y/n) [y]: " use_defaults
use_defaults=${use_defaults:-y}

if [[ "$use_defaults" != "y" ]]; then
    echo ""
    read -p "Database name [$DB_NAME]: " input
    DB_NAME=${input:-$DB_NAME}
    
    read -p "Database user [$DB_USER]: " input
    DB_USER=${input:-$DB_USER}
    
    read -sp "Database password: " DB_PASSWORD
    echo ""
fi

echo ""
print_status "Using database: $DB_NAME"
print_status "Using user: $DB_USER"

# Determine how to connect to PostgreSQL
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - usually no password needed for postgres user
    PSQL_CMD="psql postgres"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - might need sudo
    PSQL_CMD="sudo -u postgres psql"
else
    PSQL_CMD="psql postgres"
fi

# Check if database already exists
DB_EXISTS=$($PSQL_CMD -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "0")

if [ "$DB_EXISTS" = "1" ]; then
    print_warning "Database '$DB_NAME' already exists"
    read -p "Do you want to drop and recreate it? (y/n) [n]: " recreate
    recreate=${recreate:-n}
    
    if [[ "$recreate" == "y" ]]; then
        print_status "Dropping existing database..."
        $PSQL_CMD -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true
        DB_EXISTS="0"
    fi
fi

# Create database if it doesn't exist
if [ "$DB_EXISTS" != "1" ]; then
    print_status "Creating database '$DB_NAME'..."
    $PSQL_CMD -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
else
    print_status "Using existing database '$DB_NAME'"
fi

# Create user if it doesn't exist
USER_EXISTS=$($PSQL_CMD -tAc "SELECT 1 FROM pg_user WHERE usename='$DB_USER'" 2>/dev/null || echo "0")

if [ "$USER_EXISTS" != "1" ]; then
    print_status "Creating user '$DB_USER'..."
    $PSQL_CMD -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
else
    print_status "User '$DB_USER' already exists"
    read -p "Do you want to update the password? (y/n) [n]: " update_pwd
    update_pwd=${update_pwd:-n}
    
    if [[ "$update_pwd" == "y" ]]; then
        print_status "Updating password..."
        $PSQL_CMD -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || true
    fi
fi

# Grant privileges
print_status "Granting privileges..."
$PSQL_CMD -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
$PSQL_CMD -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>/dev/null || true

# Create extensions
print_status "Creating extensions..."
$PSQL_CMD -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" 2>/dev/null || true
$PSQL_CMD -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS \"pg_trgm\";" 2>/dev/null || true

# Test connection
print_status "Testing connection..."
if psql -U $DB_USER -d $DB_NAME -c "SELECT 1;" &> /dev/null; then
    print_status "Connection successful!"
else
    print_error "Connection test failed"
    exit 1
fi

# Create/update .env file
ENV_FILE=".env"
ENV_EXAMPLE="env.example"

if [ -f "$ENV_FILE" ]; then
    print_warning ".env file already exists"
    read -p "Do you want to update DATABASE_URL? (y/n) [y]: " update_env
    update_env=${update_env:-y}
else
    if [ -f "$ENV_EXAMPLE" ]; then
        print_status "Creating .env file from env.example..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        update_env="y"
    else
        print_status "Creating new .env file..."
        update_env="y"
    fi
fi

if [[ "$update_env" == "y" ]]; then
    DB_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^# DATABASE_URL=.*|DATABASE_URL=$DB_URL|" "$ENV_FILE" 2>/dev/null || \
        sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|" "$ENV_FILE" 2>/dev/null || \
        echo "DATABASE_URL=$DB_URL" >> "$ENV_FILE"
    else
        # Linux
        sed -i "s|^# DATABASE_URL=.*|DATABASE_URL=$DB_URL|" "$ENV_FILE" 2>/dev/null || \
        sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|" "$ENV_FILE" 2>/dev/null || \
        echo "DATABASE_URL=$DB_URL" >> "$ENV_FILE"
    fi
    
    print_status "Updated DATABASE_URL in .env file"
fi

echo ""
echo "============================================================"
print_status "SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "📝 Connection Details:"
echo "   Host: localhost"
echo "   Port: 5432"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo "   Connection String: postgresql://$DB_USER:****@localhost:5432/$DB_NAME"
echo ""
echo "💡 Next Steps:"
echo "   1. Review .env file configuration"
echo "   2. Install dependencies: pip install -r requirements.txt"
echo "   3. Run database migration: python3 reset_and_setup.py"
echo "   4. Start backend: python3 -m uvicorn api.main:app --reload"
echo ""
echo "📚 For more information, see POSTGRESQL_SETUP.md"
echo "============================================================"

