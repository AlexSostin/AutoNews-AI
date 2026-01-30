#!/bin/bash

# AutoNews Production Backup Script
# Usage: ./backup_production.sh [database_url]
# If database_url is not provided, it will try to use DATABASE_URL from .env

# Load .env if exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DB_URL=${1:-$DATABASE_URL}

if [ -z "$DB_URL" ]; then
    echo "❌ Error: DATABASE_URL not found. Provide it as an argument or set it in .env"
    echo "Usage: ./backup_production.sh postgres://user:pass@host:port/dbname"
    exit 1
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups"
FILENAME="$BACKUP_DIR/autonews_backup_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

echo "🔄 Starting production backup to $FILENAME..."

# Perform backup using pg_dump
if command -v pg_dump >/dev/null 2>&1; then
    pg_dump "$DB_URL" > "$FILENAME"
    if [ $? -eq 0 ]; then
        echo "✅ Backup successful: $FILENAME"
        # Compress the backup
        gzip "$FILENAME"
        echo "📦 Compressed: $FILENAME.gz"
    else
        echo "❌ Backup failed!"
        exit 1
    fi
else
    echo "❌ Error: pg_dump not found. Please install postgresql-client."
    exit 1
fi

echo "🚀 Backup process completed."
