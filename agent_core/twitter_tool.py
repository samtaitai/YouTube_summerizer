"""
Twitter Tool Module

Handles posting to Twitter/X via the Twitter API v2.
"""

import os
import requests
from typing import Dict, Any


class TwitterAPIError(Exception):
    """Base exception for Twitter API errors."""
    pass


class TwitterAuthError(TwitterAPIError):
    """Raised when authentication fails (401 Unauthorized)."""
    pass


class TwitterRateLimitError(TwitterAPIError):
    """Raised when rate limit is exceeded (429 Too Many Requests)."""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


TWITTER_API_BASE = "https://api.twitter.com/2"


def post_to_twitter(text: str, oauth_token: str) -> Dict[str, Any]:
    """
    Posts a tweet via Twitter API v2.
    
    Args:
        text: The tweet content (must be ≤280 characters)
        oauth_token: OAuth 2.0 access token with tweet.write scope
        
    Returns:
        Response dict with tweet id and text on success:
        {"data": {"id": "...", "text": "..."}}
        
    Raises:
        TwitterAuthError: If the token is invalid or expired
        TwitterRateLimitError: If rate limit is exceeded
        TwitterAPIError: For other API errors
        ValueError: If text exceeds 280 characters
    """
    # Validate text length
    if len(text) > 280:
        raise ValueError(f"Tweet exceeds 280 character limit: {len(text)} characters")
    
    endpoint = f"{TWITTER_API_BASE}/tweets"
    
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "text": text
    }
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        
        # Handle specific error codes
        if response.status_code == 401:
            raise TwitterAuthError(
                "Twitter authentication failed. Token may be invalid or expired. "
                "Please re-authenticate."
            )
        
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", 900)  # Default 15 min
            raise TwitterRateLimitError(
                f"Twitter rate limit exceeded. Try again in {retry_after} seconds.",
                retry_after=int(retry_after)
            )
        
        if response.status_code == 403:
            error_data = response.json()
            raise TwitterAPIError(
                f"Twitter API forbidden: {error_data.get('detail', 'Unknown error')}"
            )
        
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.Timeout:
        raise TwitterAPIError("Twitter API request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise TwitterAPIError(f"Twitter API request failed: {str(e)}")


def get_rate_limit_info(oauth_token: str) -> Dict[str, Any]:
    """
    Gets the current rate limit status for the tweets endpoint.
    
    Args:
        oauth_token: OAuth 2.0 access token
        
    Returns:
        Dict with rate limit info (limit, remaining, reset timestamp)
    """
    # Note: Twitter API v2 doesn't have a dedicated rate limit endpoint
    # Rate limits are returned in response headers
    # This is a placeholder for future implementation
    return {
        "endpoint": "/tweets",
        "limit": 50,  # Tweets per 15-min window for OAuth 2.0
        "note": "Rate limit info is returned in API response headers"
    }
