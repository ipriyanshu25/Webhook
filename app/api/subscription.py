from flask import Blueprint, request, jsonify
from app import mongo
from bson.objectid import ObjectId

subscription_bp = Blueprint('subscription', __name__)

# Create a new subscription
@subscription_bp.route('/', methods=['POST'])
def create_subscription():
    """Create a new webhook subscription."""
    data = request.json
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if not data.get('target_url'):
        return jsonify({"error": "Target URL is required"}), 400
    
    subscription = {
        "target_url": data['target_url'],
        "secret_key": data.get('secret_key', None),
        "event_types": data.get('event_types', None),
        "is_active": True
    }
    
    result = mongo.db.subscriptions.insert_one(subscription)
    
    # Cache the subscription data (using Redis or in-memory cache, depending on your setup)
    # You can use a similar method to cache the data (if needed)
    
    return jsonify({"subscription_id": str(result.inserted_id), "message": "Subscription created successfully"}), 201

# Get all subscriptions
@subscription_bp.route('/', methods=['GET'])
def get_subscriptions():
    """Get all webhook subscriptions."""
    subscriptions = mongo.db.subscriptions.find({"is_active": True})
    result = []
    for sub in subscriptions:
        sub['_id'] = str(sub['_id'])  # Convert ObjectId to string
        result.append(sub)
    return jsonify(result), 200

# Get a specific subscription
@subscription_bp.route('/<subscription_id>', methods=['GET'])
def get_subscription(subscription_id):
    """Get a specific webhook subscription."""
    subscription = mongo.db.subscriptions.find_one({"_id": ObjectId(subscription_id), "is_active": True})
    
    if not subscription:
        return jsonify({"error": "Subscription not found"}), 404
    
    subscription["_id"] = str(subscription["_id"])  # Convert ObjectId to string
    return jsonify(subscription), 200

# Update a subscription
@subscription_bp.route('/<subscription_id>', methods=['PUT'])
def update_subscription(subscription_id):
    """Update a webhook subscription."""
    data = request.json
    subscription = mongo.db.subscriptions.find_one({"_id": ObjectId(subscription_id), "is_active": True})
    
    if not subscription:
        return jsonify({"error": "Subscription not found"}), 404
    
    updated_data = {}
    
    if 'target_url' in data:
        updated_data['target_url'] = data['target_url']
    
    if 'secret_key' in data:
        updated_data['secret_key'] = data['secret_key']
    
    if 'event_types' in data:
        updated_data['event_types'] = data['event_types']
    
    mongo.db.subscriptions.update_one({"_id": ObjectId(subscription_id)}, {"$set": updated_data})
    
    # Invalidate the cache (if any)
    
    return jsonify({"message": "Subscription updated successfully"}), 200

# Delete a subscription (soft delete)
@subscription_bp.route('/<subscription_id>', methods=['DELETE'])
def delete_subscription(subscription_id):
    """Delete a webhook subscription (soft delete)."""
    subscription = mongo.db.subscriptions.find_one({"_id": ObjectId(subscription_id), "is_active": True})
    
    if not subscription:
        return jsonify({"error": "Subscription not found"}), 404
    
    # Set the subscription to inactive (soft delete)
    mongo.db.subscriptions.update_one({"_id": ObjectId(subscription_id)}, {"$set": {"is_active": False}})
    
    return jsonify({"message": "Subscription deleted successfully"}), 200
