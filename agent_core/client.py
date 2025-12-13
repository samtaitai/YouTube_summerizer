import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load environment variables from .env file
load_dotenv() 

def initialize_agent_client():
    """Initializes and returns the AIProjectClient."""
    try:
        # 1. Get endpoint from environment variable
        endpoint = os.getenv("PROJECT_ENDPOINT")
        if not endpoint:
            raise ValueError("PROJECT_ENDPOINT not found in .env file.")
            
        # 2. Use default credentials (requires 'az login')
        credential = DefaultAzureCredential()

        client = AIProjectClient(
            endpoint=endpoint,
            credential=credential
        )
        print("✅ AIProjectClient initialized successfully.")
        return client

    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        print("Please ensure you have run 'az login' and set PROJECT_ENDPOINT in .env")
        return None

if __name__ == "__main__":
    client = initialize_agent_client()
    
    # You can now use the client to test connections, e.g.,
    # print("Listing agents:", client.agents.list())