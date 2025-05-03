import json
import unittest
from app import create_app, mongo
from app.models.subscription import Subscription

class SubscriptionTestCase(unittest.TestCase):
    def setUp(self):
        self.app, _ = create_app({
            'TESTING': True,
            'MONGO_URI': 'mongodb://localhost:27017/testdb',
        })
        self.client = self.app.test_client()
        
        with self.app.app_context():
            mongo.db.subscriptions.drop()  # Drop the collection before each test
    
    def tearDown(self):
        with self.app.app_context():
            mongo.db.subscriptions.drop()  # Drop the collection after each test
    
    def test_create_subscription(self):
        """Test creating a new subscription"""
        subscription_data = {
            'target_url': 'https://example.com/webhook',
            'secret_key': 'test_secret',
            'event_types': 'order.created,user.updated'
        }
        
        response = self.client.post(
            '/api/subscriptions',
            data=json.dumps(subscription_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('id', data)
        self.assertEqual(data['target_url'], subscription_data['target_url'])
        self.assertEqual(data['secret_key'], '********') 
        # Check the subscription is in the database
        with self.app.app_context():
            subscription = mongo.db.subscriptions.find_one({"_id": data['id']})
            self.assertIsNotNone(subscription)
            self.assertEqual(subscription['target_url'], subscription_data['target_url'])
    
    def test_get_subscription(self):
        """Test retrieving a subscription"""
        # Create a subscription first
        subscription = Subscription(
            target_url='https://example.com/webhook',
            secret_key='test_secret',
            event_types='order.created,user.updated'
        )
        
        with self.app.app_context():
            mongo.db.subscriptions.insert_one(subscription.to_dict())
            subscription_id = str(subscription.id)
        
        # Now get the subscription
        response = self.client.get(f'/api/subscriptions/{subscription_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], subscription_id)
        self.assertEqual(data['target_url'], 'https://example.com/webhook')
    
    def test_update_subscription(self):
        """Test updating a subscription"""
        # Create a subscription first
        subscription = Subscription(
            target_url='https://example.com/webhook',
            secret_key='test_secret',
            event_types='order.created,user.updated'
        )
        
        with self.app.app_context():
            mongo.db.subscriptions.insert_one(subscription.to_dict())
            subscription_id = str(subscription.id)
        
        # Update the subscription
        update_data = {
            'target_url': 'https://updated-example.com/webhook'
        }
        
        response = self.client.put(
            f'/api/subscriptions/{subscription_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['target_url'], update_data['target_url'])
        
        # Check the subscription is updated in the database
        with self.app.app_context():
            updated_subscription = mongo.db.subscriptions.find_one({"_id": subscription_id})
            self.assertEqual(updated_subscription['target_url'], update_data['target_url'])
    
    def test_delete_subscription(self):
        """Test deleting a subscription"""
        # Create a subscription first
        subscription = Subscription(
            target_url='https://example.com/webhook',
            secret_key='test_secret'
        )
        
        with self.app.app_context():
            mongo.db.subscriptions.insert_one(subscription.to_dict())
            subscription_id = str(subscription.id)
        
        # Delete the subscription
        response = self.client.delete(f'/api/subscriptions/{subscription_id}')
        
        self.assertEqual(response.status_code, 204)
        
        # Check the subscription is deleted from the database
        with self.app.app_context():
            deleted_subscription = mongo.db.subscriptions.find_one({"_id": subscription_id})
            self.assertIsNone(deleted_subscription)
    
    def test_list_subscriptions(self):
        """Test listing all subscriptions"""
        # Create multiple subscriptions
        subscriptions = [
            Subscription(target_url='https://example.com/webhook1'),
            Subscription(target_url='https://example.com/webhook2'),
            Subscription(target_url='https://example.com/webhook3')
        ]
        
        with self.app.app_context():
            for sub in subscriptions:
                mongo.db.subscriptions.insert_one(sub.to_dict())
        
        # Get all subscriptions
        response = self.client.get('/api/subscriptions')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 3)


if __name__ == '__main__':
    unittest.main()
