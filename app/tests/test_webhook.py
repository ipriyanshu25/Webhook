import json
import unittest
from unittest.mock import patch
from app import create_app, mongo
from app.models.subscription import Subscription
from app.models.webhook import Webhook

class WebhookTestCase(unittest.TestCase):
    def setUp(self):
        self.app, _ = create_app({
            'TESTING': True,
            'MONGO_URI': 'mongodb://localhost:27017/testdb',  # MongoDB URI
        })
        self.client = self.app.test_client()
        
        with self.app.app_context():
            mongo.db.subscriptions.drop()  # Ensure fresh collection before each test
            mongo.db.webhooks.drop()  # Ensure fresh collection before each test
            
            # Create a test subscription
            self.subscription = Subscription(
                target_url='https://example.com/webhook',
                secret_key='test_secret',
                event_types='order.created,user.updated'
            )
            mongo.db.subscriptions.insert_one(self.subscription.to_dict())
            self.subscription_id = str(self.subscription.id)  # Ensure it's a string
    
    def tearDown(self):
        with self.app.app_context():
            mongo.db.subscriptions.drop()
            mongo.db.webhooks.drop()
    
    @patch('app.api.webhooks.process_webhook.delay')
    def test_ingest_webhook(self, mock_process_webhook):
        """Test ingesting a new webhook"""
        webhook_payload = {
            'event': 'order.created',
            'data': {
                'id': '12345',
                'customer': 'John Doe',
                'amount': 99.99
            }
        }
        
        response = self.client.post(
            f'/api/webhooks/ingest/{self.subscription_id}',
            data=json.dumps(webhook_payload),
            content_type='application/json',
            headers={'X-Event-Type': 'order.created'}
        )
        
        self.assertEqual(response.status_code, 202)
        data = json.loads(response.data)
        self.assertIn('id', data)
        self.assertEqual(data['status'], 'queued')
        
        # Check the webhook is in the database
        with self.app.app_context():
            webhook = mongo.db.webhooks.find_one({"_id": data['id']})
            self.assertIsNotNone(webhook)
            self.assertEqual(webhook['subscription_id'], self.subscription_id)
            self.assertEqual(webhook['status'], 'queued')
            self.assertEqual(webhook['event_type'], 'order.created')
        
        # Check that the process_webhook task was called
        mock_process_webhook.assert_called_once()
    
    @patch('app.api.webhooks.process_webhook.delay')
    def test_ingest_webhook_with_invalid_subscription(self, mock_process_webhook):
        """Test ingesting a webhook with an invalid subscription ID"""
        webhook_payload = {
            'event': 'order.created',
            'data': {
                'id': '12345',
                'customer': 'John Doe',
                'amount': 99.99
            }
        }
        
        invalid_id = '00000000-0000-0000-0000-000000000000'
        response = self.client.post(
            f'/api/webhooks/ingest/{invalid_id}',
            data=json.dumps(webhook_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        mock_process_webhook.assert_not_called()
    
    @patch('app.api.webhooks.process_webhook.delay')
    def test_ingest_webhook_with_signature(self, mock_process_webhook):
        """Test ingesting a webhook with signature verification"""
        webhook_payload = {
            'event': 'order.created',
            'data': {
                'id': '12345',
                'customer': 'John Doe',
                'amount': 99.99
            }
        }
        
        # Generate a valid signature
        import hmac
        import hashlib
        
        payload_bytes = json.dumps(webhook_payload).encode('utf-8')
        signature = hmac.new(
            key=b'test_secret',
            msg=payload_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        response = self.client.post(
            f'/api/webhooks/ingest/{self.subscription_id}',
            data=json.dumps(webhook_payload),
            content_type='application/json',
            headers={
                'X-Hub-Signature-256': f'sha256={signature}',
                'X-Event-Type': 'order.created'
            }
        )
        
        self.assertEqual(response.status_code, 202)
        mock_process_webhook.assert_called_once()
    
    @patch('app.api.webhooks.process_webhook.delay')
    def test_ingest_webhook_with_invalid_signature(self, mock_process_webhook):
        """Test ingesting a webhook with an invalid signature"""
        webhook_payload = {
            'event': 'order.created',
            'data': {
                'id': '12345',
                'customer': 'John Doe',
                'amount': 99.99
            }
        }
        
        invalid_signature = 'sha256=invalid_signature_here'
        
        response = self.client.post(
            f'/api/webhooks/ingest/{self.subscription_id}',
            data=json.dumps(webhook_payload),
            content_type='application/json',
            headers={
                'X-Hub-Signature-256': invalid_signature,
                'X-Event-Type': 'order.created'
            }
        )
        
        self.assertEqual(response.status_code, 400)
        mock_process_webhook.assert_not_called()
    
    def test_get_webhook_status(self):
        """Test getting the status of a webhook"""
        # Create a webhook first
        webhook = Webhook(
            subscription_id=self.subscription_id,
            payload={'test': 'data'},
            event_type='order.created',
            status='completed'
        )
        
        with self.app.app_context():
            mongo.db.webhooks.insert_one(webhook.to_dict())
            webhook_id = str(webhook.id)
        
        # Get the webhook status
        response = self.client.get(f'/api/webhooks/{webhook_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['id'], webhook_id)
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['subscription_id'], self.subscription_id)
    
    def test_list_webhooks_for_subscription(self):
        """Test listing webhooks for a specific subscription"""
        # Create multiple webhooks
        webhooks = [
            Webhook(subscription_id=self.subscription_id, payload={'test': '1'}, status='completed'),
            Webhook(subscription_id=self.subscription_id, payload={'test': '2'}, status='failed'),
            Webhook(subscription_id=self.subscription_id, payload={'test': '3'}, status='queued')
        ]
        
        with self.app.app_context():
            for webhook in webhooks:
                mongo.db.webhooks.insert_one(webhook.to_dict())
        
        # Get webhooks for the subscription
        response = self.client.get(f'/api/webhooks/subscription/{self.subscription_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 3)


if __name__ == '__main__':
    unittest.main()
