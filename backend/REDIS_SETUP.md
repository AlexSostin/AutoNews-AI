# Redis Setup Guide for AutoNews

Redis is used for caching API responses and improving performance. It's **optional** - the site will work without it using Django's dummy cache.

## 📦 Why Redis?

- **5-60x faster** API responses
- Reduces database load
- Caches articles, categories, tags
- Automatic cache invalidation on updates

## 🪟 Windows Installation

### Option 1: Using Memurai (Recommended)
Memurai is a Windows-native Redis alternative:

1. Download from: https://www.memurai.com/get-memurai
2. Install and run as Windows service
3. Default port: 6379 (auto-configured)

### Option 2: Using WSL (Windows Subsystem for Linux)
```bash
# Enable WSL
wsl --install

# Install Ubuntu from Microsoft Store
# Open Ubuntu terminal and run:
sudo apt update
sudo apt install redis-server

# Start Redis
sudo service redis-server start

# Test connection
redis-cli ping
# Should return: PONG
```

### Option 3: Using Docker
```bash
# Pull and run Redis container
docker run -d -p 6379:6379 --name redis redis:alpine

# Test connection
docker exec -it redis redis-cli ping
```

## 🐧 Linux Installation

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis-server

# Enable auto-start on boot
sudo systemctl enable redis-server

# Test
redis-cli ping
```

### Fedora/RHEL/CentOS
```bash
sudo dnf install redis
sudo systemctl start redis
sudo systemctl enable redis
redis-cli ping
```

## 🍎 macOS Installation

### Using Homebrew
```bash
# Install Redis
brew install redis

# Start Redis
brew services start redis

# Test
redis-cli ping
```

## 🔧 Configuration

### .env Configuration
Redis is automatically configured in `backend/.env`:

```bash
REDIS_URL=redis://127.0.0.1:6379/1
```

### Custom Redis Settings
If using different host/port:
```bash
# Remote Redis
REDIS_URL=redis://your-redis-host:6379/1

# Redis with password
REDIS_URL=redis://:password@localhost:6379/1

# Redis with SSL
REDIS_URL=rediss://localhost:6380/1
```

## ✅ Verify Installation

### Test Redis Connection
```bash
# From backend directory
cd backend
python manage.py shell

>>> from django.core.cache import cache
>>> cache.set('test', 'Hello Redis!')
>>> cache.get('test')
'Hello Redis!'
>>> exit()
```

### Check Cache Status
```python
# In Django shell
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError

try:
    cache.set('test_key', 'test_value', 10)
    result = cache.get('test_key')
    if result == 'test_value':
        print("✅ Redis is working!")
    else:
        print("⚠️ Cache returned unexpected value")
except Exception as e:
    print(f"❌ Redis error: {e}")
    print("Using dummy cache (no caching)")
```

## 🎯 What Gets Cached?

| Content Type | Cache Duration | When Cleared |
|-------------|---------------|--------------|
| Article List | 5 minutes | On article save/delete |
| Article Detail | 5 minutes | On article update |
| Categories | 1 hour | On category save/delete |
| Tags | 1 hour | On tag save/delete |
| Trending Articles | 5 minutes | On article views update |

## 🔄 Cache Management

### Clear All Caches
```bash
# From backend directory
python manage.py shell

>>> from django.core.cache import cache
>>> cache.clear()
>>> exit()
```

### Clear Specific Cache
```python
from django.core.cache import cache

# Clear article caches
cache.delete_pattern('article*')

# Clear category caches
cache.delete_pattern('category*')
```

### Flush Redis Completely
```bash
# Using redis-cli
redis-cli FLUSHDB

# Or from Python
>>> import redis
>>> r = redis.Redis()
>>> r.flushdb()
```

## 📊 Monitor Redis

### Check Memory Usage
```bash
redis-cli INFO memory
```

### Monitor Cache Hits
```bash
redis-cli INFO stats | grep hits
```

### Watch Cache Activity
```bash
redis-cli MONITOR
```

## 🚀 Production Recommendations

1. **Persistent Storage**
   ```bash
   # Edit redis.conf
   save 900 1
   save 300 10
   save 60 10000
   ```

2. **Memory Limit**
   ```bash
   maxmemory 256mb
   maxmemory-policy allkeys-lru
   ```

3. **Enable AOF (Append Only File)**
   ```bash
   appendonly yes
   appendfsync everysec
   ```

4. **Secure Redis**
   ```bash
   # Set password in redis.conf
   requirepass your_strong_password_here
   
   # Update .env
   REDIS_URL=redis://:your_strong_password_here@localhost:6379/1
   ```

5. **Use Redis Sentinel** (for high availability)
   ```bash
   # Setup Redis Sentinel for automatic failover
   redis-sentinel /path/to/sentinel.conf
   ```

## 🛠️ Troubleshooting

### Redis Not Starting
```bash
# Check if port 6379 is already in use
netstat -an | grep 6379

# Kill existing Redis process
sudo pkill redis-server

# Restart
sudo systemctl restart redis-server
```

### Connection Refused
```bash
# Check if Redis is running
sudo systemctl status redis-server

# Check Redis logs
sudo journalctl -u redis-server -n 50

# Test local connection
redis-cli ping
```

### Permission Denied
```bash
# Fix Redis directory permissions
sudo chown redis:redis /var/lib/redis
sudo chmod 750 /var/lib/redis
```

### Out of Memory
```bash
# Clear all keys
redis-cli FLUSHALL

# Or increase maxmemory in redis.conf
maxmemory 512mb
```

## 📝 Development vs Production

### Development (No Redis)
The site will automatically fall back to dummy cache:
```python
# settings.py detects missing Redis and uses:
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
```

### Production (With Redis)
For optimal performance, always use Redis in production:
- Faster API responses (5-60x)
- Lower database load
- Better user experience
- Handles traffic spikes

## 🌐 Cloud Redis Options

If you don't want to manage Redis yourself:

- **Redis Cloud** (Free tier: 30MB): https://redis.com/try-free/
- **Upstash** (Serverless Redis): https://upstash.com/
- **AWS ElastiCache**: https://aws.amazon.com/elasticache/
- **Digital Ocean Managed Redis**: https://www.digitalocean.com/products/managed-databases-redis
- **Railway** (Free tier available): https://railway.app/

Just update `REDIS_URL` in `.env` with your cloud Redis URL.

---

**Need Help?** Check Django cache documentation: https://docs.djangoproject.com/en/5.0/topics/cache/
