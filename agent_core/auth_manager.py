"""
Auth Manager Module

Handles OAuth2 authentication flows for Twitter and LinkedIn.
Uses PKCE (Proof Key for Code Exchange) for enhanced security.
"""

import os
import secrets
import hashlib
import base64
import requests
from urllib.parse import urlencode
from typing import Dict, Any, Optional
from dotenv import load_dotenv


load_dotenv()


class AuthError(Exception):
    """Base exception for authentication errors."""
    pass


# OAuth2 Configuration
OAUTH_CONFIG = {
    "twitter": {
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "revoke_url": "https://api.twitter.com/2/oauth2/revoke",
        "scopes": ["tweet.read", "tweet.write", "users.read", "offline.access"],
        "client_id_env": "TWITTER_CLIENT_ID",
        "client_secret_env": "TWITTER_CLIENT_SECRET",
    },
    "linkedin": {
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        # LinkedIn doesn't have a standard token revocation endpoint
        "revoke_url": None,
        "scopes": ["openid", "profile", "w_member_social"],
        "client_id_env": "LINKEDIN_CLIENT_ID",
        "client_secret_env": "LINKEDIN_CLIENT_SECRET",
    },
}


def _generate_pkce_verifier() -> str:
    """Generates a cryptographically random PKCE code verifier."""
    return secrets.token_urlsafe(32)


def _generate_pkce_challenge(verifier: str) -> str:
    """
    Generates a PKCE code challenge from the verifier.
    Uses SHA256 hash, base64url encoded.
    """
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


# Global registry for pending authentications to survive session resets (Streamlit specific issue)
# Format: {state: {"verifier": code_verifier, "platform": platform, "timestamp": time}}
_PENDING_AUTHS: Dict[str, Dict[str, str]] = {}


def get_oauth_url(platform: str, redirect_uri: str = None) -> tuple[str, str]:
    """
    Generates the OAuth2 authorization URL with PKCE.
    
    Args:
        platform: Platform identifier ("twitter" or "linkedin")
        redirect_uri: OAuth callback URL (defaults to env var OAUTH_REDIRECT_URI)
        
    Returns:
        Tuple of (authorization_url, state)
        The state is used to retrieve the verifier and platform after redirect.
        
    Raises:
        ValueError: If platform is not supported
        AuthError: If required credentials are missing
    """
    if platform not in OAUTH_CONFIG:
        raise ValueError(f"Unsupported platform: {platform}")
    
    config = OAUTH_CONFIG[platform]
    client_id = os.getenv(config["client_id_env"])
    
    if not client_id:
        raise AuthError(f"Missing {config['client_id_env']} in environment variables")
    
    redirect_uri = redirect_uri or os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8501/")
    
    # Generate PKCE and state values
    code_verifier = _generate_pkce_verifier()
    code_challenge = _generate_pkce_challenge(code_verifier)
    state = secrets.token_urlsafe(16)
    
    # Store verifier globally keyed by state to survive session resets
    _PENDING_AUTHS[state] = {"verifier": code_verifier, "platform": platform}
    
    # Build authorization URL
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(config["scopes"]),
        "state": state,
    }

    # Only include PKCE for Twitter as it's required. 
    # LinkedIn requires manual activation for PKCE.
    if platform == "twitter":
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    
    auth_url = f"{config['auth_url']}?{urlencode(params)}"
    
    return auth_url, state


def get_pending_auth(state: str) -> Optional[Dict[str, str]]:
    """Retrieves and removes the pending auth info for a given state."""
    return _PENDING_AUTHS.pop(state, None)


def exchange_code_for_token(
    platform: str, 
    code: str, 
    code_verifier: str,
    redirect_uri: str = None
) -> Dict[str, Any]:
    """
    Exchanges the authorization code for an access token.
    
    Args:
        platform: Platform identifier ("twitter" or "linkedin")
        code: Authorization code received from OAuth callback
        code_verifier: The PKCE verifier stored during get_oauth_url()
        redirect_uri: Must match the URI used in get_oauth_url()
        
    Returns:
        Token response dict with access_token, token_type, expires_in, etc.
        
    Raises:
        AuthError: If token exchange fails
    """
    if platform not in OAUTH_CONFIG:
        raise ValueError(f"Unsupported platform: {platform}")
    
    config = OAUTH_CONFIG[platform]
    client_id = os.getenv(config["client_id_env"])
    client_secret = os.getenv(config["client_secret_env"])
    redirect_uri = redirect_uri or os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8501/")
    
    if not client_id or not client_secret:
        raise AuthError(f"Missing OAuth credentials for {platform}")
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    
    # Only include verifier if it's Twitter (PKCE enabled)
    if platform == "twitter" and code_verifier:
        data["code_verifier"] = code_verifier
    
    # Twitter works best with Basic Auth; LinkedIn often requires credentials in the POST body
    if platform == "twitter":
        auth = (client_id, client_secret)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(config["token_url"], data=data, auth=auth, headers=headers, timeout=30)
    else:
        # LinkedIn implementation
        data["client_id"] = client_id
        data["client_secret"] = client_secret
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(config["token_url"], data=data, headers=headers, timeout=30)
    
    if response.status_code != 200:
        error_detail = response.json().get("error_description", response.text)
        raise AuthError(f"Token exchange failed: {error_detail}")
    
    return response.json()


def get_linkedin_user_urn(access_token: str) -> str:
    """
    Fetches the authenticated user's LinkedIn URN ID.
    
    Args:
        access_token: LinkedIn OAuth 2.0 access token
        
    Returns:
        The alphanumeric ID part of the user's URN (e.g., "AbC123xYz")
        
    Raises:
        AuthError: If fetching profile fails
    """
    endpoint = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=30)
        
        if response.status_code != 200:
            error_detail = response.json().get("message", response.text)
            raise AuthError(f"Failed to fetch LinkedIn user info: {error_detail}")
        
        # User ID is in the 'sub' field for OpenID Connect
        return response.json().get("sub")
    except requests.exceptions.RequestException as e:
        raise AuthError(f"LinkedIn profile request failed: {str(e)}")


def revoke_token(platform: str, token: str) -> bool:
    """
    Revokes an access token.
    
    Args:
        platform: Platform identifier
        token: The access token to revoke
        
    Returns:
        True if revocation succeeded, False otherwise
    """
    if platform not in OAUTH_CONFIG:
        return False
    
    config = OAUTH_CONFIG[platform]
    
    if not config["revoke_url"]:
        # Platform doesn't support revocation (e.g., LinkedIn)
        return True  # Consider it a success since we'll clear session anyway
    
    client_id = os.getenv(config["client_id_env"])
    client_secret = os.getenv(config["client_secret_env"])
    
    if not client_id or not client_secret:
        return False
    
    try:
        if platform == "twitter":
            auth = (client_id, client_secret)
            data = {"token": token, "token_type_hint": "access_token"}
            response = requests.post(
                config["revoke_url"], 
                data=data, 
                auth=auth,
                timeout=30
            )
        else:
            response = requests.post(
                config["revoke_url"],
                data={"token": token},
                timeout=30
            )
        
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def is_authenticated(platform: str, session_state: dict) -> bool:
    """
    Checks if a valid token exists in the session state.
    
    Args:
        platform: Platform identifier
        session_state: Streamlit session state dict
        
    Returns:
        True if token exists and appears valid
    """
    token_key = f"{platform}_token"
    token = session_state.get(token_key)
    
    if not token:
        return False
    
    # Check if it's a dict with access_token (full token response) or just the token string
    if isinstance(token, dict):
        return bool(token.get("access_token"))
    
    return bool(token)


def get_access_token(platform: str, session_state: dict) -> Optional[str]:
    """
    Extracts the access token string from session state.
    
    Args:
        platform: Platform identifier
        session_state: Streamlit session state dict
        
    Returns:
        Access token string or None
    """
    token_key = f"{platform}_token"
    token = session_state.get(token_key)
    
    if not token:
        return None
    
    if isinstance(token, dict):
        return token.get("access_token")
    
    return token
