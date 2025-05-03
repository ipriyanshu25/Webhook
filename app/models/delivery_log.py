import uuid
from datetime import datetime
from app import mongo

class DeliveryStatus:
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED_ATTEMPT = 'failed_attempt'
    FAILED = 'failed'  # Final failure after all retries

class DeliveryLog:
    def __init__(self, webhook_id, subscription_id, target_url, attempt_number=1, status=DeliveryStatus.PENDING, status_code=None, error_details=None, event_type=None):
        self.id = str(uuid.uuid4())  # Generate unique ID
        self.webhook_id = webhook_id
        self.subscription_id = subscription_id
        self.target_url = target_url
        self.attempt_number = attempt_number
        self.status = status
        self.status_code = status_code
        self.error_details = error_details
        self.created_at = datetime.utcnow()
        self.event_type = event_type

    def to_dict(self):
        """
        Convert the DeliveryLog instance into a dictionary.
        """
        return {
            "_id": self.id,
            "webhook_id": self.webhook_id,
            "subscription_id": self.subscription_id,
            "target_url": self.target_url,
            "attempt_number": self.attempt_number,
            "status": self.status,
            "status_code": self.status_code,
            "error_details": self.error_details,
            "created_at": self.created_at.isoformat(),
            "event_type": self.event_type
        }

    @classmethod
    def from_dict(cls, data):
        """
        Create a DeliveryLog instance from a dictionary.
        """
        return cls(
            webhook_id=data['webhook_id'],
            subscription_id=data['subscription_id'],
            target_url=data['target_url'],
            attempt_number=data.get('attempt_number', 1),
            status=data.get('status', DeliveryStatus.PENDING),
            status_code=data.get('status_code'),
            error_details=data.get('error_details'),
            event_type=data.get('event_type')
        )

    @classmethod
    def create_from_webhook(cls, webhook_id, subscription_id, target_url, event_type=None):
        """
        Create a new delivery log entry from the incoming webhook data.
        """
        delivery_log = cls(
            webhook_id=webhook_id,
            subscription_id=subscription_id,
            target_url=target_url,
            event_type=event_type
        )
        # Insert the log into MongoDB
        mongo.db.delivery_log.insert_one(delivery_log.to_dict())
        return delivery_log

    @classmethod
    def get_by_subscription(cls, subscription_id):
        """
        Fetch all delivery logs for a specific subscription.
        """
        logs = mongo.db.delivery_log.find({"subscription_id": subscription_id}).sort("created_at", -1)
        return [cls.from_dict(log) for log in logs]
