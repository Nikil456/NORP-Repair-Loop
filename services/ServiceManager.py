from sql_manager.DatabaseManager import DatabaseManager
from services.llm_manager.LLMManager import LLMManager
from redis_manager.RedisManager import RedisManager
from fastapi import HTTPException

class ServiceManager:
    """
    ServiceManager class to handle llm and db connections
    """
    def __init__(self, config):
        self.db_manager = None
        self.llm_manager = None
        self.initialize_services(config)

    def initialize_services(self, config):
        
        # Initialize database connection
        uri = f"{config['db_url']}?user={config['db_username']}&password={config['db_password']}"        # uri = "mysql+mysqlconnector://{name}{password}/{database name}"
        db_manager = DatabaseManager(uri)
        self.db_manager = db_manager.db

        # Initialize LLM connection
        llm_manager = LLMManager()
        self.llm_manager = llm_manager.llm
        
        # Initialize Redis connection
        self.redis_manager = RedisManager(config["redis_host_url"], config["redis_port"], config["redis_password"])

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
