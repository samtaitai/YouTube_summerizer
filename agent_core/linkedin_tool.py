"""
LinkedIn Tool Module

Handles posting to LinkedIn via the LinkedIn Marketing API (UGC Posts).
"""

import os
import requests
from typing import Dict, Any


class LinkedInAPIError(Exception):
    """Base exception for LinkedIn API errors."""
    pass


class LinkedInAuthError(LinkedInAPIError):
    """Raised when authentication fails (401 Unauthorized)."""
    pass


class LinkedInRateLimitError(LinkedInAPIError):
    """Raised when rate limit is exceeded (429 Too Many Requests)."""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def post_to_linkedin(text: str, oauth_token: str, user_urn: str) -> Dict[str, Any]:
    """
    Posts a UGC (User Generated Content) post to LinkedIn.
    
    Args:
        text: The post content (must be ≤3000 characters)
        oauth_token: OAuth 2.0 access token with w_member_social scope
        user_urn: The user's LinkedIn URN (e.g., "AbC123xYz")
        
    Returns:
        Response dict on success.
        
    Raises:
        LinkedInAuthError: If the token is invalid or expired
        LinkedInRateLimitError: If rate limit is exceeded
        LinkedInAPIError: For other API errors
        ValueError: If text exceeds 3000 characters
    """
    # Validate text length
    if len(text) > 3000:
        raise ValueError(f"LinkedIn post exceeds 3000 character limit: {len(text)} characters")
    
    endpoint = f"{LINKEDIN_API_BASE}/ugcPosts"
    
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    
    # LinkedIn UGC Post payload structure
    payload = {
        "author": f"urn:li:person:{user_urn}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": text
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        
        # Handle specific error codes
        if response.status_code == 401:
            raise LinkedInAuthError(
                "LinkedIn authentication failed. Token may be invalid or expired. "
                "Please re-authenticate."
            )
        
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", 900)
            raise LinkedInRateLimitError(
                f"LinkedIn rate limit exceeded. Try again later.",
                retry_after=int(retry_after)
            )
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                detail = error_data.get('message', error_data.get('detail', 'Unknown error'))
            except:
                detail = response.text
            raise LinkedInAPIError(f"LinkedIn API error ({response.status_code}): {detail}")
        
        return response.json()
        
    except requests.exceptions.Timeout:
        raise LinkedInAPIError("LinkedIn API request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise LinkedInAPIError(f"LinkedIn API request failed: {str(e)}")
