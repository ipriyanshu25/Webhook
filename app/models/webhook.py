from datetime import datetime
from app import mongo

class Webhook:
    def __init__(self, subscription_id, payload, event_type, status='queued'):
        self.subscription_id = subscription_id
        self.payload = payload
        self.event_type = event_type
        self.status = status
        self.timestamp = datetime.utcnow()
        self.id = None  # MongoDB will auto-generate this

    def to_dict(self):
        """
        Convert the Webhook instance into a dictionary.
        """
        return {
            "_id": self.id,
            "subscription_id": self.subscription_id,
            "payload": self.payload,
            "event_type": self.event_type,
            "status": self.status,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        """
        Create a Webhook instance from a dictionary.
        """
        return cls(
            subscription_id=data["subscription_id"],
            payload=data["payload"],
            event_type=data["event_type"],
            status=data.get("status", "queued"),
        )

    @classmethod
    def get(cls, webhook_id):
        """
        Fetch a webhook from MongoDB using the webhook ID.
        """
        webhook = mongo.db.webhooks.find_one({"_id": webhook_id})
        if webhook:
            return cls.from_dict(webhook)
        return None

    @classmethod
    def create(cls, subscription_id, payload, event_type, status="queued"):
        """
        Create and insert a new webhook into MongoDB.
        """
        webhook = cls(subscription_id, payload, event_type, status)
        result = mongo.db.webhooks.insert_one(webhook.to_dict())
        webhook.id = str(result.inserted_id)  # Set the ID after insertion
        return webhook
