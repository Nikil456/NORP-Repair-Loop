import redis


class RedisManager:
    def __init__(self, host_, port_, password_ = None):
        """
        Initialize the Redis connection.

        Args:
            host (str): The host url for redis.
            port (int): The port for the redis connection
            password (str, Optional): The password for the redis connection
        """
        redis_client = redis.Redis(
            host=host_,
            port=port_,
            password=password_,
            db=0,
            decode_responses=True
        )
        self.redis = redis_client
