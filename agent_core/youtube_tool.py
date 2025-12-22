import re
import sys
from supadata import Supadata, SupadataError

# Initialize the client
supadata = Supadata(api_key="sd_f6643070a23929dc39204b05df6bd56d")

def get_transcript_text(youtube_url: str) -> str:
    """
    Retrieves the transcript text for a given YouTube video URL.

    :param youtube_url: The full URL of the YouTube video.
    :return: The transcript text or an error message.
    """
    try:
        transcript = supadata.transcript(
        url=youtube_url,
        lang="en",  # Optional: preferred language
        text=True,  # Optional: return plain text instead of timestamped chunks
        mode="auto"  # Optional: "native", "auto", or "generate"
        )

        return transcript.content

    except SupadataError as error:
        print(f"Error code: {error.error}")
        print(f"Error message: {error.message}")
        print(f"Error details: {error.details}")
        if error.documentation_url:
            print(f"Documentation: {error.documentation_url}")

# Simple local test (optional)
if __name__ == "__main__":
    # Allow running with a command line argument
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = "https://youtu.be/EwAd-fqQfJ8?si=WXbIn7IaHRpBJ8yQ" # Example video
        
    print(f"Testing with URL: {test_url}")
    transcript = get_transcript_text(test_url)
    print("\n--- Transcript Start ---\n" + transcript + "...") 