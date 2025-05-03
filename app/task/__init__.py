from celery import Celery
from flask import Flask
from app.task.delivery import deliver_webhook
from app.task.cleanup import cleanup_logs

celery = Celery(__name__)

def init_celery(app: Flask) -> None:
    """Initialize Celery with Flask app context."""
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    
    # Setup periodic tasks for cleanup
    celery.conf.beat_schedule = {
        'cleanup-logs-every-hour': {
            'task': 'app.tasks.cleanup.cleanup_logs',
            'schedule': app.config['LOG_CLEANUP_INTERVAL'].total_seconds(),
        },
    }

    # Ensure the tasks are registered with Celery
    celery.tasks.register(deliver_webhook)
    celery.tasks.register(cleanup_logs)
