#!/bin/bash
# Скрипт для бэкапа БД AutoNews

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔄 Starting database backup..."

# Папка для бэкапов
BACKUP_DIR="$HOME/AutoNews_Backups"
mkdir -p $BACKUP_DIR

# Имя файла с датой
BACKUP_FILE="$BACKUP_DIR/autonews_backup_$(date +%Y%m%d_%H%M%S).sql"

# Получить DATABASE_URL из Railway
# Замени на твой реальный URL или используй: railway variables get DATABASE_URL
DATABASE_URL="postgresql://postgres:password@host:5432/railway"

# Сделать бэкап
echo "📦 Creating backup: $BACKUP_FILE"
pg_dump $DATABASE_URL > $BACKUP_FILE

# Проверить успешность
if [ $? -eq 0 ]; then
    # Сжать файл
    gzip $BACKUP_FILE
    BACKUP_FILE="${BACKUP_FILE}.gz"
    
    # Размер файла
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    echo -e "${GREEN}✅ Backup successful!${NC}"
    echo "📁 File: $BACKUP_FILE"
    echo "📊 Size: $SIZE"
    
    # Удалить старые бэкапы (старше 30 дней)
    find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
    echo "🗑️  Deleted backups older than 30 days"
    
else
    echo -e "${RED}❌ Backup failed!${NC}"
    exit 1
fi

# Показать список всех бэкапов
echo ""
echo "📋 All backups:"
ls -lh $BACKUP_DIR/*.sql.gz
