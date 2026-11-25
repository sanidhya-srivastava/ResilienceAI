#!/bin/sh
set -e

mkdir -p /backups /tmp/backup-staging/web-server

cat <<'EOF' > /tmp/backup-staging/web-server/nginx.conf
server {
    listen 80;
    server_name localhost;

    location /health {
        default_type application/json;
        return 200 '{"status": "running", "service": "web-server"}';
    }
}
EOF

echo "-- ResilienceAI sample DB backup" > /tmp/backup-staging/db-backup.sql

tar -czf /backups/web-server-backup-latest.tar.gz -C /tmp/backup-staging .
rm -rf /tmp/backup-staging

echo "Backup seeded at /backups/web-server-backup-latest.tar.gz"
