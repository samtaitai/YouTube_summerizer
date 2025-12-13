import re
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url: str) -> str:
    """Extracts the YouTube video ID from various URL formats."""
    # Pattern to match standard and short URLs
    pattern = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript_text(youtube_url: str) -> str:
    """
    Retrieves the full transcript text for a given YouTube URL.
    This function will be exposed as a Tool to the Foundry Agent Service.
    """
    video_id = extract_video_id(youtube_url)
    
    if not video_id:
        return f"Error: Could not extract a valid video ID from the URL: {youtube_url}"

    try:
        # Get the list of transcript parts
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
        
        # Combine the transcript parts into a single string
        full_transcript = " ".join([item['text'] for item in transcript_list])
        
        return f"SUCCESS: Transcript retrieved. Length: {len(full_transcript)} characters. Now, summarize the following text: {full_transcript}"
        
    except Exception as e:
        # Handle cases where the video has no captions
        return f"FAILURE: Could not retrieve captions for the video ID {video_id}. Error: {e}"

# Simple local test (optional)
if __name__ == "__main__":
    test_url = "https://youtu.be/u47GtXwePms?si=lzKq2N-ARpNcHuGO" # Example video
    transcript = get_transcript_text(test_url)
    print(transcript[:200] + "...") # Print the start of the transcript