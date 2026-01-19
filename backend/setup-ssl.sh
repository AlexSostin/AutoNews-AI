#!/bin/bash

# SSL Certificate Setup Script for Let's Encrypt
# Запустите этот скрипт ПОСЛЕ того как DNS записи вашего домена указывают на сервер

set -e

# ===== НАСТРОЙКИ =====
DOMAIN="yourdomain.com"
EMAIL="your-email@example.com"
STAGING=0  # Установите 1 для тестирования (staging режим)

# =====================

echo "🔐 Настройка SSL сертификатов для $DOMAIN"
echo "=================================="

# Проверка что домен задан
if [ "$DOMAIN" = "yourdomain.com" ]; then
    echo "❌ ОШИБКА: Измените переменную DOMAIN в скрипте на ваш реальный домен!"
    exit 1
fi

# Проверка email
if [ "$EMAIL" = "your-email@example.com" ]; then
    echo "❌ ОШИБКА: Измените переменную EMAIL в скрипте на ваш реальный email!"
    exit 1
fi

# Создаем директории
echo "📁 Создание директорий..."
mkdir -p ./nginx/ssl
mkdir -p ./certbot/conf
mkdir -p ./certbot/www

# Временный Nginx конфиг для получения сертификата (без SSL)
echo "📝 Создание временного Nginx конфига..."
cat > ./nginx/nginx.temp.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name _;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
}
EOF

# Запускаем временный Nginx
echo "🚀 Запуск временного Nginx..."
docker run --rm -d \
    --name nginx_temp \
    -p 80:80 \
    -v $(pwd)/nginx/nginx.temp.conf:/etc/nginx/nginx.conf:ro \
    -v $(pwd)/certbot/www:/var/www/certbot \
    nginx:alpine

sleep 3

# Получаем сертификат
echo "📜 Запрос SSL сертификата от Let's Encrypt..."

if [ $STAGING -eq 1 ]; then
    echo "⚠️  STAGING режим - тестовый сертификат!"
    STAGING_ARG="--staging"
else
    STAGING_ARG=""
fi

docker run --rm \
    -v $(pwd)/certbot/conf:/etc/letsencrypt \
    -v $(pwd)/certbot/www:/var/www/certbot \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    $STAGING_ARG \
    -d $DOMAIN \
    -d www.$DOMAIN

# Останавливаем временный Nginx
echo "🛑 Остановка временного Nginx..."
docker stop nginx_temp

# Копируем сертификаты в нужную директорию
echo "📋 Копирование сертификатов..."
cp ./certbot/conf/live/$DOMAIN/fullchain.pem ./nginx/ssl/
cp ./certbot/conf/live/$DOMAIN/privkey.pem ./nginx/ssl/

# Обновляем конфиг Nginx с правильным доменом
echo "🔧 Обновление Nginx конфига..."
sed -i "s/yourdomain.com/$DOMAIN/g" ./nginx/nginx.conf

echo ""
echo "✅ Сертификаты успешно установлены!"
echo "📍 Сертификаты находятся в: ./nginx/ssl/"
echo ""
echo "Следующие шаги:"
echo "1. Проверьте конфиг: nginx/nginx.conf"
echo "2. Запустите production: docker-compose -f docker-compose.prod.yml up -d"
echo "3. Проверьте сайт: https://$DOMAIN"
echo ""
echo "🔄 Сертификаты будут обновляться автоматически каждые 12 часов"
