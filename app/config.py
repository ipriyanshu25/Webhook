import os
from datetime import timedelta

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # MongoDB (Replacing SQLAlchemy with MongoDB)
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/webhook_service')

    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Celery
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # Webhook Service
    WEBHOOK_DELIVERY_TIMEOUT = int(os.environ.get('WEBHOOK_DELIVERY_TIMEOUT', 10))  # seconds
    WEBHOOK_MAX_RETRIES = int(os.environ.get('WEBHOOK_MAX_RETRIES', 5))
    WEBHOOK_RETRY_DELAYS = [10, 30, 60, 300, 900]  # seconds (10s, 30s, 1m, 5m, 15m)
    
    # Log Retention
    LOG_RETENTION_PERIOD = timedelta(hours=int(os.environ.get('LOG_RETENTION_HOURS', 72)))
    LOG_CLEANUP_INTERVAL = timedelta(hours=int(os.environ.get('LOG_CLEANUP_INTERVAL_HOURS', 1)))
    
    # Cache
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))  # 5 minutes
    SUBSCRIPTION_CACHE_TIMEOUT = int(os.environ.get('SUBSCRIPTION_CACHE_TIMEOUT', 600))  # 10 minutes
