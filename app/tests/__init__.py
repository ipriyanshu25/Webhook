import unittest

# This is where you can configure the test suite if needed
# For example, if you wanted to collect all tests from submodules:
# from .test_webhook import WebhookTestCase
# from .test_subscription import SubscriptionTestCase

# Or you can use the following to discover and run tests:
def run_tests():
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="tests", pattern="test_*.py")
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    run_tests()
