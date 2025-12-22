import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    FunctionTool,
    ListSortOrder,
)

# Import your custom tool function from the local file
from .youtube_tool import get_transcript_text
from .event_handler import MyEventHandler

# --- Configuration ---
load_dotenv() 

project_endpoint = os.getenv("PROJECT_ENDPOINT")
model_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4o")
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential()
)
user_functions = {get_transcript_text}
functions = FunctionTool(user_functions)
agent_instructions = (
        "You are an expert YouTube summarizer. Your only job is to analyze the user's input. "
        "If the input contains a YouTube URL, you MUST call the `get_transcript_text` function tool "
        "first. Once you receive the transcript, generate a concise, easy-to-read summary of the key points. "
        "If the transcript fails, report the error. Do NOT invent information."
    )

# --- Core Agent Logic ---

def summarize_youtube_video(youtube_url: str):
    """
    Creates a thread, sends the URL, runs the agent, and retrieves the summary.
    """
    print(f"\n--- Starting Summarization for: {youtube_url} ---")
    
    with project_client:
        agents_client = project_client.agents
        functions = FunctionTool(user_functions)
        agent = agents_client.create_agent(
            model=model_name,
            name="YouTubeSummarizerAgent",
            instructions=agent_instructions,
            tools=functions.definitions,
        )
        # [END create_agent_with_function_tool]
        print(f"Created agent, ID: {agent.id}")

        thread = agents_client.threads.create()
        print(f"Created thread, ID: {thread.id}")

        # Send the URL message
        user_message = f"Please summarize the content of this YouTube video: {youtube_url}"

        message = agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

        with agents_client.runs.stream(
            thread_id=thread.id,
            agent_id=agent.id,
            event_handler=MyEventHandler(functions, agents_client)
        ) as stream:
            stream.until_done()

        agents_client.delete_agent(agent_id=agent.id)
        print("Deleted agent.")

        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)     
        for msg in messages:
            if msg.text_messages:
                last_text = msg.text_messages[-1]
                print("\n--- FINAL SUMMARY ---\n")
                print(last_text.text['value'])
                print("\n---------------------\n")
            
            else:
                print("🤷 Could not retrieve final summary message.")

# --- Main Execution Block ---

if __name__ == "__main__":
    try:
        # Example URL (replace with your test URL)
        test_url = "https://youtu.be/EwAd-fqQfJ8?si=WXbIn7IaHRpBJ8yQ" 
        
        summarize_youtube_video(test_url)
 
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")