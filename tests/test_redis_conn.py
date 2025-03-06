import unittest
import redis

class TestRedisConnection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Setup the Redis client before running tests."""
        cls.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        try:
            # Test the connection
            cls.redis_client.ping()
            print("Connected to Redis!")
        except redis.ConnectionError as e:
            raise RuntimeError("Could not connect to Redis. Ensure the server is running.") from e

    def test_set_and_get_key(self):
        """Test setting and getting a key-value pair."""
        key, value = "test_key", "test_value"
        
        # Set a key
        result = self.redis_client.set(key, value)
        self.assertTrue(result, "Failed to set the key in Redis.")
        
        # Get the key
        retrieved_value = self.redis_client.get(key)
        self.assertEqual(retrieved_value, value, "The value retrieved does not match the value set.")

    def test_delete_key(self):
        """Test deleting a key."""
        key, value = "test_key_to_delete", "test_value"
        
        # Set a key
        self.redis_client.set(key, value)
        
        # Delete the key
        result = self.redis_client.delete(key)
        self.assertEqual(result, 1, "Failed to delete the key from Redis.")
        
        # Ensure the key no longer exists
        retrieved_value = self.redis_client.get(key)
        self.assertIsNone(retrieved_value, "The key should no longer exist in Redis.")

    @classmethod
    def tearDownClass(cls):
        """Clean up any test keys after all tests."""
        keys_to_delete = ["test_key", "test_key_to_delete"]
        cls.redis_client.delete(*keys_to_delete)

if __name__ == "__main__":
    unittest.main()
