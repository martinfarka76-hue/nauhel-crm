#!/bin/bash
set -e
cd ~/crm
DATE=$(date +%Y-%m-%d_%H-%M)
BACKUP_DIR=/tmp/crm-backup-$DATE
mkdir -p "$BACKUP_DIR"

docker compose exec -T postgres pg_dump -U crm_user nauhel_crm > "$BACKUP_DIR/database.sql"
rsync -a --exclude=postgres --exclude=n8n ~/crm/data/ "$BACKUP_DIR/data/"

rclone copy "$BACKUP_DIR" "onedrive:CRM-zalohy/$DATE" --create-empty-src-dirs

rm -rf "$BACKUP_DIR"

# smaž zálohy starší než 30 dní ze SharePointu
rclone delete --min-age 30d "onedrive:CRM-zalohy" 2>/dev/null || true

echo "Záloha $DATE dokončena."
