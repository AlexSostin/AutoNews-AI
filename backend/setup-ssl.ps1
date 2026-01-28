# SSL Setup Script for Windows (PowerShell)
# Запустите ПОСЛЕ того как DNS записи указывают на ваш сервер

param(
    [Parameter(Mandatory=$true)]
    [string]$Domain,
    
    [Parameter(Mandatory=$true)]
    [string]$Email,
    
    [switch]$Staging
)

Write-Host "🔐 Настройка SSL сертификатов для $Domain" -ForegroundColor Cyan
Write-Host "=================================="

# Создаем директории
Write-Host "📁 Создание директорий..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path ".\nginx\ssl" | Out-Null
New-Item -ItemType Directory -Force -Path ".\certbot\conf" | Out-Null
New-Item -ItemType Directory -Force -Path ".\certbot\www" | Out-Null

# Временный Nginx конфиг
Write-Host "📝 Создание временного Nginx конфига..." -ForegroundColor Yellow
$tempConfig = @"
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
"@
$tempConfig | Out-File -FilePath ".\nginx\nginx.temp.conf" -Encoding UTF8

# Запускаем временный Nginx
Write-Host "🚀 Запуск временного Nginx..." -ForegroundColor Yellow
$currentPath = (Get-Location).Path
docker run --rm -d `
    --name nginx_temp `
    -p 80:80 `
    -v "${currentPath}\nginx\nginx.temp.conf:/etc/nginx/nginx.conf:ro" `
    -v "${currentPath}\certbot\www:/var/www/certbot" `
    nginx:alpine

Start-Sleep -Seconds 3

# Получаем сертификат
Write-Host "📜 Запрос SSL сертификата от Let's Encrypt..." -ForegroundColor Yellow

$stagingArg = if ($Staging) { 
    Write-Host "⚠️  STAGING режим - тестовый сертификат!" -ForegroundColor Yellow
    "--staging" 
} else { 
    "" 
}

docker run --rm `
    -v "${currentPath}\certbot\conf:/etc/letsencrypt" `
    -v "${currentPath}\certbot\www:/var/www/certbot" `
    certbot/certbot certonly `
    --webroot `
    --webroot-path=/var/www/certbot `
    --email $Email `
    --agree-tos `
    --no-eff-email `
    $stagingArg `
    -d $Domain `
    -d "www.$Domain"

# Останавливаем временный Nginx
Write-Host "🛑 Остановка временного Nginx..." -ForegroundColor Yellow
docker stop nginx_temp

# Копируем сертификаты
Write-Host "📋 Копирование сертификатов..." -ForegroundColor Yellow
Copy-Item ".\certbot\conf\live\$Domain\fullchain.pem" ".\nginx\ssl\" -Force
Copy-Item ".\certbot\conf\live\$Domain\privkey.pem" ".\nginx\ssl\" -Force

# Обновляем конфиг Nginx
Write-Host "🔧 Обновление Nginx конфига..." -ForegroundColor Yellow
$nginxConfig = Get-Content ".\nginx\nginx.conf" -Raw
$nginxConfig = $nginxConfig -replace "yourdomain.com", $Domain
$nginxConfig | Out-File ".\nginx\nginx.conf" -Encoding UTF8

Write-Host ""
Write-Host "✅ Сертификаты успешно установлены!" -ForegroundColor Green
Write-Host "📍 Сертификаты находятся в: .\nginx\ssl\" -ForegroundColor Green
Write-Host ""
Write-Host "Следующие шаги:"
Write-Host "1. Проверьте конфиг: nginx\nginx.conf"
Write-Host "2. Запустите production: docker-compose -f docker-compose.prod.yml up -d"
Write-Host "3. Проверьте сайт: https://$Domain"
Write-Host ""
Write-Host "🔄 Сертификаты будут обновляться автоматически каждые 12 часов" -ForegroundColor Cyan

# Пример использования:
Write-Host ""
Write-Host "Пример запуска:" -ForegroundColor Gray
Write-Host ".\setup-ssl.ps1 -Domain 'example.com' -Email 'admin@example.com'" -ForegroundColor Gray
Write-Host "Тестовый режим: .\setup-ssl.ps1 -Domain 'example.com' -Email 'admin@example.com' -Staging" -ForegroundColor Gray
