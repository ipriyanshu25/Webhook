import uuid
import json
from flask import Blueprint, request, jsonify
from app import mongo
from app.utils.cache import get_cached_subscription
from app.utils.signature import verify_signature
from app.task.delivery import deliver_webhook

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/ingest/<subscription_id>', methods=['POST'])
def ingest_webhook(subscription_id):
    """
    Ingest a webhook payload for a specific subscription.
    
    This endpoint accepts an incoming webhook payload, validates it if a secret
    is present, and queues it for asynchronous delivery.
    """
    # Get subscription (first from cache, then from DB)
    subscription_data = get_cached_subscription(subscription_id)
    if not subscription_data:
        subscription = mongo.db.subscriptions.find_one({"_id": ObjectId(subscription_id), "is_active": True})
        if not subscription:
            return jsonify({"error": "Subscription not found"}), 404
        subscription_data = subscription

    # Parse the incoming payload
    try:
        payload = request.get_data(as_text=True)
        payload_json = json.loads(payload)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON payload: {str(e)}"}), 400
    
    # Verify signature if secret is present (bonus feature)
    if subscription_data.get('secret_key'):
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return jsonify({"error": "Missing signature header"}), 400
        
        if not verify_signature(payload, signature, subscription_data['secret_key']):
            return jsonify({"error": "Invalid signature"}), 401
    
    # Check event type filtering (bonus feature)
    event_type = request.headers.get('X-Event-Type')
    if event_type and subscription_data.get('event_types'):
        if event_type not in subscription_data['event_types']:
            return jsonify({"message": "Event type not matched, skipping delivery"}), 202
    
    # Generate a unique ID for this webhook delivery
    webhook_id = str(uuid.uuid4())
    
    # Queue the webhook delivery task
    deliver_webhook.delay(
        webhook_id=webhook_id,
        subscription_id=subscription_id,
        payload=payload,
        event_type=event_type
    )
    
    return jsonify({
        "message": "Webhook received and queued for delivery",
        "webhook_id": webhook_id
    }), 202
