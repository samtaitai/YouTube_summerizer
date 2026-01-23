"""
Platform Adapter Module

Maps platform names to configuration and orchestrates platform-specific operations.
"""

from typing import Callable, Dict, Any, Optional


PLATFORM_CONFIG: Dict[str, Dict[str, Any]] = {
    "twitter": {
        "max_chars": 280,
        "tone": "casual, engaging, use hashtags",
        "post_function": "post_to_twitter",
        "display_name": "Twitter/X",
    },
    "linkedin": {
        "max_chars": 3000,
        "tone": "professional, structured, use bullet points",
        "post_function": "post_to_linkedin",
        "display_name": "LinkedIn",
    },
    "default": {
        "max_chars": None,  # No limit
        "tone": "informative, concise",
        "post_function": None,
        "display_name": "Default",
    },
}


def get_platform_config(platform: str) -> Dict[str, Any]:
    """
    Returns configuration for the given platform.
    
    Args:
        platform: Platform identifier ("twitter", "linkedin", "default")
        
    Returns:
        Configuration dictionary with max_chars, tone, post_function, display_name
        
    Raises:
        ValueError: If platform is not supported
    """
    if platform not in PLATFORM_CONFIG:
        supported = ", ".join(PLATFORM_CONFIG.keys())
        raise ValueError(f"Unsupported platform: '{platform}'. Supported: {supported}")
    return PLATFORM_CONFIG[platform]


def validate_summary_length(text: str, platform: str) -> bool:
    """
    Validates that the summary text meets the platform's character limit.
    
    Args:
        text: The summary text to validate
        platform: Target platform identifier
        
    Returns:
        True if text is within limit, False otherwise
    """
    config = get_platform_config(platform)
    max_chars = config.get("max_chars")
    
    if max_chars is None:
        return True  # No limit for this platform
    
    return len(text) <= max_chars


def get_character_count(text: str) -> int:
    """Returns the character count of the given text."""
    return len(text)


def format_length_error(text: str, platform: str) -> str:
    """
    Formats an error message when summary exceeds platform limit.
    
    Args:
        text: The summary text that exceeded the limit
        platform: Target platform identifier
        
    Returns:
        Formatted error message with details
    """
    config = get_platform_config(platform)
    max_chars = config.get("max_chars")
    current_len = len(text)
    
    if max_chars is None:
        return ""
    
    excess = current_len - max_chars
    return (
        f"Summary exceeds {config['display_name']} limit by {excess} characters. "
        f"Current: {current_len}, Max: {max_chars}"
    )
