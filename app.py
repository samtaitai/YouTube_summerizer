import streamlit as st
from urllib.parse import urlparse, parse_qs

from agent_core.agent_client import summarize_youtube_video, summarize_for_platform
from agent_core import auth_manager
from agent_core.twitter_tool import post_to_twitter, TwitterAPIError, TwitterAuthError, TwitterRateLimitError
from agent_core.linkedin_tool import post_to_linkedin, LinkedInAPIError, LinkedInAuthError, LinkedInRateLimitError

# --- Page Configuration ---
st.set_page_config(page_title="YouTube Summarizer", page_icon="📺", layout="wide")

# --- Session State Initialization ---
if "twitter_token" not in st.session_state:
    st.session_state["twitter_token"] = None
if "linkedin_token" not in st.session_state:
    st.session_state["linkedin_token"] = None
if "linkedin_urn" not in st.session_state:
    st.session_state["linkedin_urn"] = None
if "twitter_auth_url" not in st.session_state:
    st.session_state["twitter_auth_url"] = None
if "linkedin_auth_url" not in st.session_state:
    st.session_state["linkedin_auth_url"] = None
if "pending_post" not in st.session_state:
    st.session_state["pending_post"] = None  # Stores the generated post awaiting confirmation

# --- OAuth Callback Handler ---
query_params = st.query_params
if "code" in query_params:
    state = query_params.get("state")
    if isinstance(state, list):
        state = state[0]
        
    pending_auth = auth_manager.get_pending_auth(state) if state else None
    
    if pending_auth:
        try:
            code = query_params["code"]
            if isinstance(code, list):
                code = code[0]
                
            platform = pending_auth["platform"]
            verifier = pending_auth["verifier"]
            
            token_response = auth_manager.exchange_code_for_token(
                platform,
                code,
                verifier
            )
            
            st.session_state[f"{platform}_token"] = token_response
            st.session_state[f"{platform}_auth_url"] = None
            
            # For LinkedIn, we also need to fetch the User URN
            if platform == "linkedin":
                access_token = auth_manager.get_access_token("linkedin", st.session_state)
                urn = auth_manager.get_linkedin_user_urn(access_token)
                st.session_state["linkedin_urn"] = urn
                
            st.query_params.clear()
            st.success(f"🎉 Successfully connected to {platform.capitalize()}!")
            st.rerun()
        except auth_manager.AuthError as e:
            st.error(f"Authentication failed: {e}")
            st.query_params.clear()
    else:
        # Check if we're not authenticated to any platform and show warning
        if not (st.session_state.get("twitter_token") or st.session_state.get("linkedin_token")):
            st.warning("⚠️ Authentication session expired. Please try logging in again.")
        st.query_params.clear()

# --- Sidebar: Authentication ---
with st.sidebar:
    st.header("🔐 Connect Accounts")
    
    # Twitter Authentication
    if not auth_manager.is_authenticated("twitter", st.session_state):
        if not st.session_state.get("twitter_auth_url"):
            try:
                auth_url, _ = auth_manager.get_oauth_url("twitter")
                st.session_state["twitter_auth_url"] = auth_url
            except Exception as e:
                st.error(f"Error initializing Twitter login: {e}")
        
        if st.session_state.get("twitter_auth_url"):
            st.link_button("🐦 Login with Twitter", st.session_state["twitter_auth_url"], use_container_width=True)
    else:
        st.success("✓ Twitter connected")
        if st.button("Logout Twitter", use_container_width=True):
            token = auth_manager.get_access_token("twitter", st.session_state)
            if token:
                auth_manager.revoke_token("twitter", token)
            st.session_state["twitter_token"] = None
            st.session_state["twitter_auth_url"] = None
            st.rerun()

    st.divider()

    # LinkedIn Authentication
    if not auth_manager.is_authenticated("linkedin", st.session_state):
        if not st.session_state.get("linkedin_auth_url"):
            try:
                auth_url, _ = auth_manager.get_oauth_url("linkedin")
                st.session_state["linkedin_auth_url"] = auth_url
            except Exception as e:
                st.error(f"Error initializing LinkedIn login: {e}")
        
        if st.session_state.get("linkedin_auth_url"):
            st.link_button("🔗 Login with LinkedIn", st.session_state["linkedin_auth_url"], use_container_width=True)
    else:
        st.success("✓ LinkedIn connected")
        if st.button("Logout LinkedIn", use_container_width=True):
            st.session_state["linkedin_token"] = None
            st.session_state["linkedin_urn"] = None
            st.session_state["linkedin_auth_url"] = None
            st.rerun()
    
    st.divider()
    st.caption("ℹ️ Posting limits: Twitter (~50/day), LinkedIn (varies)")

# --- Main Content ---
st.title("📺 YouTube Video Summarizer")
st.write("Enter a YouTube URL below to get a concise summary generated by an AI agent.")

def clear_input():
    st.session_state["youtube_url"] = ""
    st.session_state["pending_post"] = None

def cancel_post():
    st.session_state["pending_post"] = None

# --- Confirmation Flow: If there's a pending post, show confirmation UI ---
if st.session_state.get("pending_post"):
    pending = st.session_state["pending_post"]
    platform = pending.get("platform", "twitter")
    limit = 3000 if platform == "linkedin" else 280
    
    st.markdown("---")
    st.subheader(f"📝 Proposed {platform.capitalize()} Post")
    st.info(pending["text"])
    
    color = "green" if len(pending['text']) <= limit else "red"
    st.markdown(f"**Character count:** :{color}[{len(pending['text'])}/{limit}]")
    
    # Custom CSS for the Post button color (pale green)
    st.markdown("""
        <style>
        /* Target the first button in the confirmation container */
        div.stButton > button[kind="primary"] {
            background-color: #c8e6c9 !important;
            color: #1b5e20 !important;
            border: 1px solid #a5d6a7 !important;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #a5d6a7 !important;
            border-color: #81c784 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        button_text = f"✅ Post to {platform.capitalize()}"
        if st.button(button_text, type="primary", use_container_width=True):
            with st.spinner("Posting..."):
                try:
                    token = auth_manager.get_access_token(platform, st.session_state)
                    if platform == "twitter":
                        result = post_to_twitter(pending["text"], token)
                        tweet_id = result.get("data", {}).get("id")
                        st.success(f"✅ Posted! [View tweet](https://twitter.com/i/web/status/{tweet_id})")
                    else:
                        urn = st.session_state.get("linkedin_urn")
                        result = post_to_linkedin(pending["text"], token, urn)
                        st.success("✅ Successfully posted to LinkedIn!")
                        
                    st.session_state["pending_post"] = None
                except (TwitterAuthError, LinkedInAuthError) as e:
                    st.error(f"🔒 {e}")
                    st.session_state[f"{platform}_token"] = None
                    st.session_state["pending_post"] = None
                except (TwitterRateLimitError, LinkedInRateLimitError) as e:
                    st.error(f"⏱️ {e}")
                except (TwitterAPIError, LinkedInAPIError, ValueError) as e:
                    st.error(f"❌ Failed: {e}")
    with col2:
        if st.button("❌ Cancel", use_container_width=True, on_click=cancel_post):
            pass  # on_click handles this
    
    st.stop()  # Don't show the rest of the UI while confirming

# --- Normal Input Flow ---
youtube_url = st.text_input(
    "YouTube URL", 
    placeholder="https://www.youtube.com/watch?v=...", 
    key="youtube_url"
)

platform_options = ["Default", "Twitter", "LinkedIn"]
selected_platform = st.selectbox(
    "Summary Format",
    options=platform_options,
    index=0,
    help="Select target platform for optimized summary format"
)

platform_map = {"Default": "default", "Twitter": "twitter", "LinkedIn": "linkedin"}
platform = platform_map.get(selected_platform, "default")

if platform != "default":
    st.info(f"📱 {selected_platform} mode: Summary will be optimized for {selected_platform}.")
    if not auth_manager.is_authenticated(platform, st.session_state):
        st.warning(f"⚠️ Connect {selected_platform} in sidebar to post directly.")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    summarize_only = st.button("📝 Summarize Video", type="primary")
with col2:
    can_post = platform != "default" and auth_manager.is_authenticated(platform, st.session_state)
    summarize_and_post = st.button(
        "📝 Summarize & Post",
        disabled=not can_post,
        help=f"Generate & post to {platform.capitalize()}" if can_post else f"Login to {platform.capitalize()} first"
    )
with col3:
    st.button("🔄 Reset", on_click=clear_input)

if summarize_only or summarize_and_post:
    if not youtube_url:
        st.error("Please enter a valid YouTube URL.")
    else:
        with st.spinner("Processing..."):
            try:
                if platform == "default":
                    summary = summarize_youtube_video(youtube_url)
                    st.success("Generated Successfully!")
                    st.markdown(f"### Summary\n{summary}")
                else:
                    summary = summarize_for_platform(youtube_url, platform)
                    
                    if platform == "twitter":
                        # Build final tweet
                        hashtags = " #AI #Summary"
                        url_length = 23  # Twitter standard
                        char_count = len(summary) + len(hashtags) + 1 + url_length
                        
                        if char_count > 280:
                            max_summary_len = 280 - len(hashtags) - 24 - 3 
                            summary = summary[:max_summary_len] + "..."
                            st.warning("⚠️ Summary truncated to fit Twitter limit.")
                        
                        final_post = f"{summary}{hashtags} {youtube_url}"
                        limit = 280
                    else:
                        # LinkedIn
                        final_post = f"{summary}\n\nSource: {youtube_url}"
                        limit = 3000
                    
                    if summarize_and_post:
                        # Store for confirmation
                        st.session_state["pending_post"] = {
                            "text": final_post, 
                            "url": youtube_url,
                            "platform": platform
                        }
                        st.rerun()
                    else:
                        # Just display
                        st.success("Generated Successfully!")
                        color = "green" if len(final_post) <= limit else "red"
                        st.markdown(f"**Character count:** :{color}[{len(final_post)}/{limit}]")
                        st.markdown(f"### Proposed Post\n{final_post}")
                        
            except Exception as e:
                st.error(f"An error occurred: {e}")