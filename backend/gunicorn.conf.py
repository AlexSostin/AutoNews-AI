# ========================================
# GUNICORN Configuration for Production
# ========================================
# Файл: backend/gunicorn.conf.py

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8001"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"  # Используйте 'gevent' или 'eventlet' для async
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "autonews_gunicorn"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (если нужно терминировать SSL на Gunicorn, а не на Nginx)
# keyfile = "/path/to/privkey.pem"
# certfile = "/path/to/fullchain.pem"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Debugging (только для development!)
# reload = True
# reload_extra_files = []

def on_starting(server):
    """
    Called just before the master process is initialized.
    """
    print("🚀 Gunicorn server starting...")

def on_reload(server):
    """
    Called to recycle workers during a reload via SIGHUP.
    """
    print("🔄 Gunicorn reloading...")

def when_ready(server):
    """
    Called just after the server is started.
    """
    print("✅ Gunicorn server ready!")

def pre_fork(server, worker):
    """
    Called just before a worker is forked.
    """
    pass

def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    """
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """
    Called just before a new master process is forked.
    """
    server.log.info("Forked child, re-executing.")

def worker_int(worker):
    """
    Called just after a worker exited on SIGINT or SIGQUIT.
    """
    worker.log.info(f"Worker interrupted (pid: {worker.pid})")

def worker_abort(worker):
    """
    Called when a worker received the SIGABRT signal.
    """
    worker.log.info(f"Worker aborted (pid: {worker.pid})")
