from flask import Blueprint, jsonify
from app import mongo

status_bp = Blueprint('status', __name__)

@status_bp.route('/status/<string:task_id>', methods=['GET'])
def get_status(task_id):
    """
    Fetch the delivery status of a specific task.
    """
    task = mongo.db.delivery_log.find_one({"task_id": task_id})
    
    if task:
        return jsonify({
            "task_id": task["task_id"],
            "subscription_id": task["subscription_id"],
            "target_url": task["target_url"],
            "timestamp": task["timestamp"],
            "attempt_number": task["attempt_number"],
            "outcome": task["outcome"],
            "status_code": task["status_code"],
            "error_details": task.get("error_details", None)
        }), 200
    else:
        return jsonify({"message": "Task not found"}), 404

@status_bp.route('/status/subscription/<string:subscription_id>', methods=['GET'])
def get_subscription_status(subscription_id):
    """
    Fetch the status of the last 20 delivery attempts for a specific subscription.
    """
    tasks = mongo.db.delivery_log.find({"subscription_id": subscription_id}).sort([("timestamp", -1)]).limit(20)
    
    if tasks.count() > 0:
        response = []
        for task in tasks:
            response.append({
                "task_id": task["task_id"],
                "timestamp": task["timestamp"],
                "attempt_number": task["attempt_number"],
                "outcome": task["outcome"],
                "status_code": task["status_code"],
                "error_details": task.get("error_details", None)
            })
        return jsonify(response), 200
    else:
        return jsonify({"message": "No tasks found for this subscription"}), 404
