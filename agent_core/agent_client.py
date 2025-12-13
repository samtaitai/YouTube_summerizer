import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import FunctionTool, ToolSet, MessageRole, FunctionDefinition
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from typing import Set

# Import your custom tool function from the local file
from .youtube_tool import get_transcript_text

# --- Configuration ---
load_dotenv() 

MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4o") 
AGENT_NAME = "YouTubeSummarizerAgent"
# Ensure the ID is safe and consistent
AGENT_ID = f"asst_{AGENT_NAME.lower().replace('-', '_')}" 

# Define the list of custom tools the agent can use.
# The FunctionTool inspects the Python function, including its docstring and
# signature, to understand how to call it.
YOUTUBE_TOOLS = FunctionTool(functions={get_transcript_text})

# --- Core Agent Logic ---

def get_agents_client() -> AgentsClient:
    """Initializes and returns the dedicated AgentsClient."""
    endpoint = os.getenv("PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError("PROJECT_ENDPOINT not found in .env file.")
        
    agents_client = AgentsClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential()
    )
    return agents_client

def get_agent_config():
    """Defines the common configuration parameters for create/update."""
    
    # 1. Create a ToolSet from the list of defined tools.
    toolset = ToolSet()
    toolset.add(YOUTUBE_TOOLS)
    
    # 3. Define the instructions (System Prompt)
    agent_instructions = (
        "You are an expert YouTube summarizer. Your only job is to analyze the user's input. "
        "If the input contains a YouTube URL, you MUST call the `get_transcript_text` function tool "
        "first. Once you receive the transcript, generate a concise, easy-to-read summary of the key points. "
        "If the transcript fails, report the error. Do NOT invent information."
    )
    
    return {
        "model": MODEL_DEPLOYMENT_NAME,
        "name": AGENT_NAME,
        "instructions": agent_instructions,
        "toolset": toolset,
    }

def create_or_update_summarizer_agent(client: AgentsClient):
    """
    Checks if the agent exists. If yes, updates it. If no, creates it.
    """
    config = get_agent_config()
    
    try:
        # 1. Check if the agent exists
        client.get_agent(agent_id=AGENT_ID)
        
        # 2. If it exists, update it
        print(f"🔄 Agent with ID '{AGENT_ID}' found. Updating configuration...")
        agent = client.update_agent(
            agent_id=AGENT_ID,
            model=config["model"],
            instructions=config["instructions"],
            toolset=config["toolset"],
            name=config["name"]
        )
        print(f"✅ Agent '{agent.name}' (ID: {agent.id}) updated.")
        return agent

    except ResourceNotFoundError:
        # 3. If it does NOT exist (404), create it
        print(f"➕ Agent with ID '{AGENT_ID}' not found. Creating a new one...")
        agent = client.create_agent(**config)
        print(f"✅ Agent '{agent.name}' (ID: {agent.id}) created.")
        return agent
    
    except HttpResponseError as e:
        # Catch any other HTTP-related errors (permissions, bad model name, etc.)
        print(f"❌ An HTTP error occurred during agent management: Status {e.status_code}. Message: {e.message}")
        raise e

def summarize_youtube_video(agents_client: AgentsClient, youtube_url: str):
    """
    Creates a thread, sends the URL, runs the agent, and retrieves the summary.
    """
    print(f"\n--- Starting Summarization for: {youtube_url} ---")
    
    # Ensure the agent exists and tools are registered
    agent = create_or_update_summarizer_agent(agents_client)

    # 1. Send the URL message
    user_message = f"Please summarize the content of this YouTube video: {youtube_url}"
    
    print(f"🔑 Creating thread and processing run with Agent ID: {agent.id}")
    
    # Create a ToolSet containing the callable Python functions for local execution.
    local_toolset = ToolSet()
    local_toolset.add(YOUTUBE_TOOLS)
    
    # Create a thread and process the run with the initial user message.
    run = agents_client.create_thread_and_process_run(
        agent_id=agent.id,
        toolset=local_toolset, # Provide the ToolSet for local execution
        thread={ # The initial message to start the conversation
            "messages": [{"role": MessageRole.USER, "content": user_message}]
        }
    )
    
    # 2. Extract the thread ID from the run object
    thread_id = run.thread_id
    
    # 3. Check status and retrieve the final message (rest of the logic remains)
    if run.status == "failed":
        print(f"❌ Agent Run Failed: {run.error.message}")
        return
        
    # Use the .messages property on the AgentsClient to get the MessagesOperations,
    # then call list() to retrieve all messages for the given thread_id.
    thread_messages = list(agents_client.messages.list(thread_id=thread_id))

    # The assistant's reply will be the last message in the thread.
    if thread_messages:
        # Extract text from each content part of the last message
        last_message = thread_messages[0]
        final_content = last_message.content[0].text['value'] if last_message.content[0].type == "text" else "No text content found."
        print("\n--- FINAL SUMMARY ---\n")
        print(final_content)
        print("\n---------------------\n")
    else:
        print("🤷 Could not retrieve final summary message.")

# --- Main Execution Block ---

if __name__ == "__main__":
    try:
        agents_client = get_agents_client()
        
        # Example URL (replace with your test URL)
        test_url = "https://youtu.be/YlCfCJjYlTY?si=uDXA0j1u7Hao7zah" 
        
        summarize_youtube_video(agents_client, test_url)
 
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")