#!/bin/bash
set -e

# Configure PostgreSQL to accept password authentication from all hosts
echo "Configuring PostgreSQL authentication..."
cat >> "$PGDATA/pg_hba.conf" <<EOF

# Allow password authentication from Docker network
host    all             all             0.0.0.0/0               md5
EOF

# Reload PostgreSQL configuration
pg_ctl reload -D "$PGDATA"

echo "PostgreSQL configuration updated successfully"
