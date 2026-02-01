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
user_functions = {get_transcript_text}
functions = FunctionTool(user_functions)
def get_instructions(platform: str = "default") -> str:
    """
    Returns platform-specific agent instructions.
    
    Args:
        platform: "default" | "twitter" | "linkedin"
    
    Returns:
        Instruction string tailored to the target platform.
    """
    if platform == "twitter":
        return (
            "You are a Twitter content expert. Your task is to extract the SINGLE most important insight from a video and turn it into a tiny tweet. "
            "CRITICAL CONSTRAINT: Your response MUST be UNDER 150 characters. This is non-negotiable. "
            "Leave at least 130 characters of space for a URL and hashtags that will be added later. "
            "\n\nSTEPS: "
            "1. Call `get_transcript_text` to get the video content. "
            "2. Identify the ONE most punchy point. "
            "3. Write a single short sentence (e.g. 'X is changing everything because of Y!'). "
            "4. VERIFY your count is < 150 chars. "
            "\n\nFORMAT: Return ONLY the raw text. No quotes, intro, or hashtags. "
            "If transcript fails, respond with 'Error: Transcript unavailable' (under 30 chars)."
        )
    elif platform == "linkedin":
        return (
            "You are a LinkedIn content strategist. Summarize a video for a professional audience. "
            "CONSTRAINT: Your response MUST be UNDER 2800 characters to leave room for a URL. "
            "\n\nSTEPS: "
            "1. Call `get_transcript_text` to get the video content. "
            "2. Identify 3-5 key insights or takeaways. "
            "3. Structure using bullet points or numbered list. "
            "4. Use a professional, value-driven tone (e.g. 'Key insight for [industry]:'). "
            "\n\nFORMAT: Return ONLY the summary text. No intro preamble. "
            "If transcript fails, respond with 'Error: Transcript unavailable'."
        )
    # Default instructions (original behavior)
    return (
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
    
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential()
    )

    with project_client:
        agents_client = project_client.agents
        functions = FunctionTool(user_functions)
        agent = agents_client.create_agent(
            model=model_name,
            name="YouTubeSummarizerAgent",
            instructions=get_instructions("default"),
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

        summary_text = "No summary generated."
        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.DESCENDING)
        for msg in messages:
            if msg.role == "assistant" and msg.text_messages:
                last_text = msg.text_messages[-1]
                summary_text = last_text.text['value']
                print("\n--- FINAL SUMMARY ---\n")
                print(summary_text)
                print("\n---------------------\n")
                break
        
        return summary_text


def summarize_for_platform(youtube_url: str, platform: str) -> str:
    """
    Wrapper that generates a platform-optimized summary.
    
    This function calls the summarization logic with platform-specific instructions.
    The summary is validated against the platform's character limit.
    
    Args:
        youtube_url: The YouTube video URL to summarize
        platform: Target platform ("default" | "twitter" | "linkedin")
        
    Returns:
        Platform-optimized summary string
        
    Raises:
        ValueError: If summary exceeds platform character limit
    """
    from .platform_adapter import validate_summary_length, format_length_error
    
    print(f"\n--- Starting Platform Summarization for: {youtube_url} ({platform}) ---")
    
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential()
    )

    with project_client:
        agents_client = project_client.agents
        functions = FunctionTool(user_functions)
        
        # Use platform-specific instructions
        instructions = get_instructions(platform)
        
        agent = agents_client.create_agent(
            model=model_name,
            name=f"YouTubeSummarizerAgent-{platform}",
            instructions=instructions,
            tools=functions.definitions,
        )
        print(f"Created agent, ID: {agent.id}")

        thread = agents_client.threads.create()
        print(f"Created thread, ID: {thread.id}")

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

        summary_text = "No summary generated."
        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.DESCENDING)
        for msg in messages:
            if msg.role == "assistant" and msg.text_messages:
                last_text = msg.text_messages[-1]
                summary_text = last_text.text['value']
                print(f"\n--- FINAL {platform.upper()} SUMMARY ---\n")
                print(summary_text)
                print("\n---------------------\n")
                break
        
        # Validate character limit for the platform
        if not validate_summary_length(summary_text, platform):
            error_msg = format_length_error(summary_text, platform)
            print(f"WARNING: {error_msg}")
            # Still return the summary but log the warning
        
        return summary_text

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