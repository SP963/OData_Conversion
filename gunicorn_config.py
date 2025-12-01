# Gunicorn configuration for production deployment
import os
import multiprocessing

# Server socket configuration
bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "trp-api"

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn/trp-api.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None
cert_reqs = 0
ca_certs = None
ciphers = "TLSv1"

# Application
preload_app = False
raw_env = []


# Server hooks
def when_ready(server):
    print("Gunicorn server is ready. Spawning workers")


def on_exit(server):
    print("Gunicorn server exited")
