import uuid
from datetime import datetime
from app import mongo

class Subscription:
    def __init__(self, target_url, secret_key=None, event_types=None, is_active=True):
        self.target_url = target_url
        self.secret_key = secret_key
        self.event_types = event_types
        self.is_active = is_active
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at

    def to_dict(self):
        """
        Convert the Subscription instance into a dictionary.
        """
        return {
            "_id": str(self.id),
            "target_url": self.target_url,
            "has_secret": bool(self.secret_key),  # Don't expose the actual secret
            "event_types": self.event_types.split(',') if self.event_types else [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active
        }

    @classmethod
    def from_dict(cls, data):
        """
        Create a Subscription instance from a dictionary.
        """
        return cls(
            target_url=data['target_url'],
            secret_key=data.get('secret_key'),
            event_types=','.join(data.get('event_types', [])) if data.get('event_types') else None,
            is_active=data.get('is_active', True)
        )

    @classmethod
    def get(cls, subscription_id):
        """
        Fetch a subscription from MongoDB using subscription ID.
        """
        subscription = mongo.db.subscriptions.find_one({"_id": ObjectId(subscription_id)})
        if subscription:
            return cls.from_dict(subscription)
        return None

    @classmethod
    def get_all(cls):
        """
        Fetch all active subscriptions from MongoDB.
        """
        subscriptions = mongo.db.subscriptions.find({"is_active": True})
        return [cls.from_dict(sub) for sub in subscriptions]

    def save(self):
        """
        Save a subscription to the MongoDB database.
        """
        subscription_data = self.to_dict()
        # Insert or update based on whether the subscription already exists
        if hasattr(self, 'id'):  # Check if the subscription already has an ID (update)
            mongo.db.subscriptions.update_one(
                {"_id": ObjectId(self.id)}, {"$set": subscription_data}, upsert=True
            )
        else:  # New subscription, create it
            result = mongo.db.subscriptions.insert_one(subscription_data)
            self.id = str(result.inserted_id)  # Set the ID after insertion

    def update(self, data):
        """
        Update subscription details.
        """
        self.target_url = data.get('target_url', self.target_url)
        self.secret_key = data.get('secret_key', self.secret_key)
        self.event_types = ','.join(data.get('event_types', [])) if data.get('event_types') else self.event_types
        self.updated_at = datetime.utcnow()
        self.save()

    def delete(self):
        """
        Soft delete a subscription (set is_active to False).
        """
        mongo.db.subscriptions.update_one({"_id": ObjectId(self.id)}, {"$set": {"is_active": False}})
