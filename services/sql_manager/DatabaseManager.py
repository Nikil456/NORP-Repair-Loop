from langchain_community.utilities import SQLDatabase

class DatabaseManager:
    def __init__(self, uri="sqlite:///Chinook.db"):
        """
        Initialize the database connection.

        Args:
            uri (str): The uri of the database.
        """
        # Update below for connecting with local MySQL database
        self.db = SQLDatabase.from_uri(uri)

    def execute(self, query):
        """
        Method to execute the SQL query and return the results.
        """
        self.db.run(query)
