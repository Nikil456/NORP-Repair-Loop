from langchain_community.utilities import SQLDatabase

class DatabaseManager:
    def __init__(self, uri="mysql+mysqlconnector://root:password@localhost/norp_db"):
        """
        Initialize the database connection.

        Args:
            uri (str): The uri of the database.
        """
        # Initialize the MySQL database connection
        self.db = SQLDatabase.from_uri(uri)

    def execute(self, query):
        """
        Method to execute the SQL query and return the results.
        """
        self.db.run(query)
