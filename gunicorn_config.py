import multiprocessing
import os

# Worker configuration - adaptive to system resources
cpu_count = multiprocessing.cpu_count()
workers = max(2, min(cpu_count, 4))  # At least 2, at most 4 workers
threads = max(2, min(cpu_count * 2, 8))  # At least 2, at most 8 threads
worker_class = 'gthread'  # Using threads instead of processes

# Binding
bind = '0.0.0.0:5001'  # Match the port from Flask config

# Timeout configuration
timeout = 120
keepalive = 5

# Logging - simplified configuration
accesslog = None     # Disable access logging
errorlog = '-'       # Log errors to stderr
loglevel = 'warning' # Reduce Gunicorn startup noise

# Process naming
proc_name = 'streetview_app'

# Debugging
reload = False       # Set to True for development
capture_output = True  # Capture Flask output
enable_stdio_inheritance = True  # Ensure Flask logs are properly captured

# Server mechanics
daemon = False
pidfile = None      # Don't create a pidfile in container
