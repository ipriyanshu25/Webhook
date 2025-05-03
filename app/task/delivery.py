import uuid
import time
import json
from bson import ObjectId
import requests
from celery import shared_task
from flask import current_app
from app import mongo
from app.models.subscription import Subscription
from app.models.delivery_log import DeliveryLog, DeliveryStatus
from app.utils.cache import get_cached_subscription

@shared_task(bind=True, max_retries=None)  # We handle retries manually
def deliver_webhook(self, webhook_id, subscription_id, payload, event_type=None):
    """
    Task to deliver a webhook payload to the target URL.
    
    This task attempts to deliver the webhook payload to the subscription's
    target URL. If delivery fails, it will retry according to the configured
    retry strategy with exponential backoff.
    
    Args:
        webhook_id (str): Unique ID for this webhook delivery
        subscription_id (str): ID of the subscription to deliver to
        payload (str): JSON payload to deliver
        event_type (str, optional): Type of event being delivered
    """
    # Get subscription details (from cache or DB)
    subscription_data = get_cached_subscription(subscription_id)
    if not subscription_data:
        subscription = mongo.db.subscriptions.find_one({"_id": ObjectId(subscription_id), "is_active": True})
        if not subscription:
            # Subscription not found or inactive, log and exit
            log = DeliveryLog(
                webhook_id=webhook_id,
                subscription_id=subscription_id,
                target_url="unknown",
                attempt_number=1,
                event_type=event_type
            )
            log.status = DeliveryStatus.FAILED
            log.error_details = "Subscription not found or inactive"
            mongo.db.delivery_log.insert_one(log.to_dict())
            return
        
        subscription_data = subscription

    # Determine attempt number
    previous_attempts = mongo.db.delivery_log.count_documents(
        {"webhook_id": webhook_id}
    )
    
    attempt_number = previous_attempts + 1
    
    # Check if we've exceeded the max retries
    if attempt_number > current_app.config['WEBHOOK_MAX_RETRIES']:
        # Log the final failure
        log = DeliveryLog(
            webhook_id=webhook_id,
            subscription_id=subscription_id,
            target_url=subscription_data['target_url'],
            attempt_number=attempt_number,
            event_type=event_type
        )
        log.status = DeliveryStatus.FAILED
        log.error_details = f"Exceeded maximum retry attempts ({current_app.config['WEBHOOK_MAX_RETRIES']})"
        mongo.db.delivery_log.insert_one(log.to_dict())
        return
    
    # Create a delivery log for this attempt
    log = DeliveryLog(
        webhook_id=webhook_id,
        subscription_id=subscription_id,
        target_url=subscription_data['target_url'],
        attempt_number=attempt_number,
        event_type=event_type
    )
    mongo.db.delivery_log.insert_one(log.to_dict())
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Webhook-Delivery-Service/1.0',
        'X-Webhook-ID': webhook_id
    }
    
    if event_type:
        headers['X-Event-Type'] = event_type
    
    # Attempt delivery
    try:
        response = requests.post(
            subscription_data['target_url'],
            data=payload,
            headers=headers,
            timeout=current_app.config['WEBHOOK_DELIVERY_TIMEOUT']
        )
        
        # Update the log with the result
        log.status_code = response.status_code
        
        if 200 <= response.status_code < 300:
            # Success
            log.status = DeliveryStatus.SUCCESS
        else:
            # Failed attempt
            log.status = DeliveryStatus.FAILED_ATTEMPT
            log.error_details = f"HTTP {response.status_code}: {response.text[:500]}"
            
            # Schedule a retry with exponential backoff
            retry_delays = current_app.config['WEBHOOK_RETRY_DELAYS']
            retry_index = min(attempt_number - 1, len(retry_delays) - 1)
            retry_delay = retry_delays[retry_index]
            
            # Schedule the retry
            deliver_webhook.apply_async(
                args=[webhook_id, subscription_id, payload, event_type],
                countdown=retry_delay
            )
    
    except Exception as e:
        # Handle network errors, timeouts, etc.
        log.status = DeliveryStatus.FAILED_ATTEMPT
        log.error_details = f"Error: {str(e)}"
        
        # Schedule a retry with exponential backoff
        retry_delays = current_app.config['WEBHOOK_RETRY_DELAYS']
        retry_index = min(attempt_number - 1, len(retry_delays) - 1)
        retry_delay = retry_delays[retry_index]
        
        # Schedule the retry
        deliver_webhook.apply_async(
            args=[webhook_id, subscription_id, payload, event_type],
            countdown=retry_delay
        )
    
    finally:
        # Update the log in the database
        mongo.db.delivery_log.update_one(
            {"_id": log.id},
            {"$set": log.to_dict()}
        )
