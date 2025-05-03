from datetime import datetime
from celery import shared_task
from flask import current_app
from app import mongo

@shared_task
def cleanup_logs():
    """
    Periodic task to delete old delivery logs based on retention policy.
    
    This task runs periodically to delete logs that are older than the
    configured retention period (default: 72 hours).
    """
    retention_period = current_app.config['LOG_RETENTION_PERIOD']
    cutoff_date = datetime.utcnow() - retention_period
    
    # Delete logs older than the retention period
    result = mongo.db.delivery_log.delete_many({"created_at": {"$lt": cutoff_date}})
    
    return {'deleted_before': cutoff_date.isoformat(), 'deleted_count': result.deleted_count}
