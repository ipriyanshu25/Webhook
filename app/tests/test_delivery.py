import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app import create_app, mongo
from app.models.subscription import Subscription
from app.models.delivery_log import DeliveryLog, DeliveryStatus
from app.task.delivery import deliver_webhook
from app.task.cleanup import cleanup_logs

class DeliveryTestCase(unittest.TestCase):
    def setUp(self):
        self.app, self.celery = create_app({
            'TESTING': True,
            'MONGO_URI': 'mongodb://localhost:27017/testdb',
            'MAX_RETRIES': 3,
            'RETRY_DELAYS': [1, 2, 3],  # Shorter delays for testing
            'DELIVERY_TIMEOUT': 2,  # Shorter timeout for testing
            'LOG_RETENTION_PERIOD': 2  # 2 hours for testing
        })
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # MongoDB setup: Create test subscription
        self.subscription = Subscription(
            target_url='https://example.com/webhook',
            secret_key='test_secret',
            event_types='order.created,user.updated'
        )
        mongo.db.subscriptions.insert_one(self.subscription.to_dict())
        self.subscription_id = self.subscription.id
        
        # Create a test webhook
        self.webhook = {
            "subscription_id": self.subscription_id,
            "payload": {"test": "data"},
            "event_type": "order.created",
            "status": "queued"
        }
        mongo.db.webhooks.insert_one(self.webhook)
        self.webhook_id = self.webhook["_id"]
    
    def tearDown(self):
        mongo.db.subscriptions.delete_many({})
        mongo.db.webhooks.delete_many({})
        mongo.db.delivery_log.delete_many({})
        self.app_context.pop()
    
    @patch('requests.post')
    def test_successful_webhook_delivery(self, mock_post):
        """Test successful webhook delivery"""
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_post.return_value = mock_response
        
        # Process the webhook (call the task directly for testing)
        with self.app.app_context():
            deliver_webhook(self.webhook_id, self.subscription_id, json.dumps(self.webhook["payload"]), self.webhook["event_type"])
            
            # Check that the webhook status was updated (MongoDB update)
            webhook = mongo.db.webhooks.find_one({"_id": self.webhook_id})
            self.assertEqual(webhook["status"], "completed")
            
            # Check that a delivery log was created
            logs = mongo.db.delivery_log.find({"webhook_id": self.webhook_id})
            self.assertEqual(logs.count(), 1)
            log = logs[0]
            self.assertEqual(log["status"], DeliveryStatus.SUCCESS)
            self.assertEqual(log["status_code"], 200)
            self.assertEqual(log["attempt_number"], 1)
    
    @patch('requests.post')
    @patch('app.tasks.webhook_delivery.retry_webhook.apply_async')
    def test_failed_webhook_delivery_with_retry(self, mock_retry, mock_post):
        """Test failed webhook delivery with retry"""
        # Mock a failed response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_post.return_value = mock_response
        
        # Process the webhook (call the task directly for testing)
        with self.app.app_context():
            deliver_webhook(self.webhook_id, self.subscription_id, json.dumps(self.webhook["payload"]), self.webhook["event_type"])
            
            # Check that the webhook status was updated (still processing due to retry)
            webhook = mongo.db.webhooks.find_one({"_id": self.webhook_id})
            self.assertEqual(webhook["status"], "processing")  # Still processing due to pending retries
            
            # Check that a delivery log was created
            logs = mongo.db.delivery_log.find({"webhook_id": self.webhook_id})
            self.assertEqual(logs.count(), 1)
            log = logs[0]
            self.assertEqual(log["status"], DeliveryStatus.FAILED_ATTEMPT)
            self.assertEqual(log["status_code"], 500)
            self.assertEqual(log["attempt_number"], 1)
            
            # Verify that retry was scheduled
            mock_retry.assert_called_once()
            args, kwargs = mock_retry.call_args
            self.assertEqual(kwargs["args"], (self.webhook_id, 2))  # Second attempt
    
    @patch('requests.post')
    def test_max_retries_reached(self, mock_post):
        """Test webhook delivery when max retries is reached"""
        # Mock a failed response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # Create delivery logs for previous attempts
        for attempt in range(1, 3):  # 1, 2 attempts
            log = DeliveryLog(
                webhook_id=self.webhook_id,
                attempt_number=attempt,
                status=DeliveryStatus.FAILED_ATTEMPT,
                status_code=500,
                timestamp=datetime.utcnow()
            )
            mongo.db.delivery_log.insert_one(log.to_dict())
        
        # Process the webhook (3rd attempt, max is 3)
        with self.app.app_context():
            deliver_webhook(self.webhook_id, self.subscription_id, json.dumps(self.webhook["payload"]), self.webhook["event_type"])
            
            # Check that the webhook status was updated to failed
            webhook = mongo.db.webhooks.find_one({"_id": self.webhook_id})
            self.assertEqual(webhook["status"], "failed")
            
            # Check that a final delivery log was created
            logs = mongo.db.delivery_log.find({"webhook_id": self.webhook_id}).sort("attempt_number")
            self.assertEqual(logs.count(), 3)
            log = logs[-1]
            self.assertEqual(log["status"], DeliveryStatus.FAILED)
            self.assertEqual(log["attempt_number"], 3)
    
    def test_cleanup_old_logs(self):
        """Test cleanup of old delivery logs"""
        # Create some old logs
        old_time = datetime.utcnow() - timedelta(hours=3)  # 3 hours ago
        
        for i in range(5):
            log = DeliveryLog(
                webhook_id=self.webhook_id,
                attempt_number=i+1,
                status=DeliveryStatus.SUCCESS,
                status_code=200,
                timestamp=old_time
            )
            mongo.db.delivery_log.insert_one(log.to_dict())
        
        # Create some recent logs
        for i in range(3):
            log = DeliveryLog(
                webhook_id=self.webhook_id,
                attempt_number=i+1,
                status=DeliveryStatus.SUCCESS,
                status_code=200,
                timestamp=datetime.utcnow()
            )
            mongo.db.delivery_log.insert_one(log.to_dict())
        
        # Run the cleanup task
        with self.app.app_context():
            cleanup_logs()
            
            # Check that only recent logs remain
            logs = mongo.db.delivery_log.find()
            self.assertEqual(logs.count(), 3)  # Only the 3 recent logs should remain
    
    def test_delivery_logs_for_webhook(self):
        """Test retrieving delivery logs for a specific webhook"""
        # Create some delivery logs
        for i in range(3):
            log = DeliveryLog(
                webhook_id=self.webhook_id,
                attempt_number=i+1,
                status=DeliveryStatus.FAILED_ATTEMPT if i < 2 else DeliveryStatus.SUCCESS,
                status_code=500 if i < 2 else 200,
                timestamp=datetime.utcnow()
            )
            mongo.db.delivery_log.insert_one(log.to_dict())
        
        # Get logs through API
        client = self.app.test_client()
        response = client.get(f'/api/logs/webhook/{self.webhook_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 3)
        
        # Logs should be in reverse chronological order (newest first)
        self.assertEqual(data[0]['attempt_number'], 3)
        self.assertEqual(data[0]['status'], DeliveryStatus.SUCCESS)
        self.assertEqual(data[1]['attempt_number'], 2)
        self.assertEqual(data[1]['status'], DeliveryStatus.FAILED_ATTEMPT)
    
    def test_recent_delivery_logs_for_subscription(self):
        """Test retrieving recent delivery logs for a subscription"""
        # Create another webhook for the same subscription
        webhook2 = {
            "subscription_id": self.subscription_id,
            "payload": {"test": "data2"},
            "event_type": "user.updated",
            "status": "completed"
        }
        mongo.db.webhooks.insert_one(webhook2)
        webhook2_id = webhook2["_id"]
        
        # Create delivery logs for both webhooks
        for webhook_id in [self.webhook_id, webhook2_id]:
            for i in range(2):
                log = DeliveryLog(
                    webhook_id=webhook_id,
                    attempt_number=i+1,
                    status=DeliveryStatus.SUCCESS,
                    status_code=200,
                    timestamp=datetime.utcnow()
                )
                mongo.db.delivery_log.insert_one(log.to_dict())
        
        # Get logs through API
        client = self.app.test_client()
        response = client.get(f'/api/logs/subscription/{self.subscription_id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 4)  # 2 logs for each of 2 webhooks


if __name__ == '__main__':
    unittest.main()
