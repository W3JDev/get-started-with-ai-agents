# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.
# See LICENSE file in the project root for full license information.

import multiprocessing
import os

# Gunicorn configuration for the AI agent application
bind = f"0.0.0.0:{os.getenv('PORT', '50505')}"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Application factory
def worker_int(worker):
    """Handle worker interrupt signal"""
    worker.log.info("worker received INT or QUIT signal")

# Application module
module_name = "api.main:create_app"

# Enable access logs
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Preload the application
preload_app = True

# Enable hot reloading in development
if not os.getenv("RUNNING_IN_PRODUCTION"):
    reload = True