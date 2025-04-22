import requests
import json

# Note: Using port 8088 based on the original curl command example. 
# Change if your server runs on a different port (e.g., 8000).
DEFAULT_URL = "http://localhost:8088/query" 

def send_hardcoded_query(url: str = DEFAULT_URL):
    """
    Sends a hardcoded query to the FastAPI backend.

    Args:
        url: The URL of the query endpoint.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "session_id": "123",
        "question": "For each zipcode, get mean commute time and average housing value.",
        "message_type": "human",  # Assuming message_type is always 'human' for a client query
        "use_rag": True,
        "use_auto_correction": False,
        "generate_summary": False  # Default to True to maintain current behavior
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        print("Request successful!")
        print("Response JSON:")
        try:
            print(json.dumps(response.json(), indent=2))
        except json.JSONDecodeError:
            print("Response content (not valid JSON):")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"Error sending request: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    send_hardcoded_query()
    # If you need to specify a different URL, you can pass it:
    # send_hardcoded_query(url="http://your-other-url:port/query") 