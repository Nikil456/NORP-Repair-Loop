from services.sql_manager.DatabaseManager import DatabaseManager
from services.llm_manager.LLMManager import LLMManager
from services.redis_manager.RedisManager import RedisManager
from fastapi import HTTPException

class ServiceManager:
    """
    ServiceManager class to handle llm and db connections
    """
    def __init__(self, config):
        self.db_manager = None
        self.llm_manager = None
        self.redis_manager = None
        self.initialize_services(config)

    def initialize_services(self, config):
        """
        Initialize all services with the provided configuration.
        
        Args:
            config: Configuration dictionary containing database, Redis, and LLM settings
        """
        if not config:
            raise ValueError("Configuration is required to initialize services")
            
        # Initialize database connection
        uri = config.get('db_url', "sqlite:///local_norp.db")  # SQLite URI format: "sqlite:///database_name.db"
        db_manager = DatabaseManager(uri)
        self.db_manager = db_manager.db

        # Initialize LLM connection - pass the config to ensure API key is used
        llm_manager = LLMManager(config=config)
        self.llm_manager = llm_manager.llm
        
        # Initialize Redis connection
        redis_host = config.get("redis_host_url", "localhost")
        redis_port = config.get("redis_port", "6379")
        redis_password = config.get("redis_password", None)
        self.redis_manager = RedisManager(redis_host, redis_port, redis_password)

    def get_db(self):
        if not self.db_manager:
            raise HTTPException(status_code=500, detail="Database connection not initialized.")
        return self.db_manager

    def get_llm(self):
        if not self.llm_manager:
            raise HTTPException(status_code=500, detail="LLM connection not initialized.")
        return self.llm_manager
    
    def get_redis(self):
        if not self.redis_manager:
            raise HTTPException(status_code=500, detail="Redis connection not initialized.")
        return self.redis_manager
