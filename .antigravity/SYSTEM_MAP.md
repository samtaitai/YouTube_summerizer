# Workspace System Map: YouTube Summarizer

This document serves as the primary architectural reference for the YouTube Summarizer project.

## 1. Core Architectural Patterns

*   **UI Layer (Streamlit):** Monolithic frontend built with Streamlit (`app.py`). Handles user input, session state, OAuth callbacks, platform selection, and post confirmation flow.
*   **Orchestration (Azure AI Agents):** Decentralized logic using the Azure AI Agents SDK. The system utilizes an "Agent" that manages conversation state (Threads) and autonomous tool invocation.
*   **Decoupled Tooling:** Functional separation of concerns. The `agent_core/youtube_tool.py` acts as an adapter for the Supadata API, keeping business logic separate from AI instructions.
*   **Event-Handler Pattern:** Real-time monitoring and reaction to the Agent's run-cycle through `agent_core/event_handler.py`.
*   **Social Media Adapter Pattern:** `platform_adapter.py` + `twitter_tool.py` + `auth_manager.py` enable posting to social platforms without modifying core summarization logic.

## 2. Primary Data Flow

### Default Summarization
1.  **Input:** User enters a URL into the Streamlit text field.
2.  **Initialization:** `app.py` triggers `summarize_youtube_video()`.
3.  **Agent Creation:** An AI Project Client is initialized, and a temporary agent is provisioned via Azure AI Foundry.
4.  **Threading:** A unique conversation thread is created for the request.
5.  **Reasoning Loop:**
    *   Agent identifies the need for a transcript based on the user prompt.
    *   Agent requests a "Tool Call" to `get_transcript_text`.
    *   `MyEventHandler` executes the local Python function and sends the output back to the stream.
6.  **External Link:** `Supadata` retrieves transcripts from YouTube.
7.  **Final Synthesis:** The LLM (gpt-4.1-mini) summarizes the provided transcript.
8.  **Output:** Streamlit displays the Markdown response.

### Twitter Posting Flow
1.  **Authentication:** User clicks "Login with Twitter" → redirects to Twitter OAuth → returns with token stored in `st.session_state`.
2.  **Summary Generation:** `summarize_for_platform(url, "twitter")` uses platform-specific instructions targeting <150 characters.
3.  **Post Assembly:** App appends hashtags (`#AI #Summary`) and YouTube URL to summary.
4.  **Confirmation:** User sees proposed post with "Post to Twitter" / "Cancel" buttons.
5.  **Posting:** `post_to_twitter()` sends tweet via API v2.

## 3. Component Breakdown

| File | Responsibility |
| :--- | :--- |
| `app.py` | Entry point, Streamlit UI, OAuth callback, platform selection, confirmation flow. |
| `agent_core/agent_client.py` | Azure AI Client lifecycle, `get_instructions(platform)`, `summarize_for_platform()`. |
| `agent_core/youtube_tool.py` | Integration with Supadata API for transcript retrieval. |
| `agent_core/event_handler.py` | Logic for handling streaming events and tool execution during runs. |
| `agent_core/platform_adapter.py` | Platform config (Twitter/LinkedIn), character limit validation. |
| `agent_core/twitter_tool.py` | Twitter API v2 posting with `TwitterAuthError`, `TwitterRateLimitError`. |
| `agent_core/auth_manager.py` | OAuth2 with PKCE, global verifier registry for session persistence. |
| `role.json` | Azure RBAC custom role definition for necessary permissions. |
| `tests/test_platform_adapter.py` | Unit tests for platform adapter and instructions. |

## 4. Technical Debt & Optimization Roadmap

| Priority | Issue | Status | Notes |
|:---------|:------|:-------|:------|
| Critical | Agent Lifecycle (create/delete per request) | Open | Adds ~3-5s latency. Fix: Use persistent Agent ID. |
| Medium | Hardcoded Prompts | ✅ Resolved | Moved to `get_instructions(platform)` function. |
| Medium | Sync Blocking UI | Open | Fix: Async processing or Streamlit fragments. |
| Low | Thread Persistence | Open | Store Thread IDs for "Recent Summaries" feature. |
| Low | Retry Logic | Open | Minimal retry for API failures/timeouts. |

## 5. Feature Status

| Feature | Status | Notes |
|:--------|:-------|:------|
| YouTube Summarization | ✅ Complete | Original functionality |
| Twitter OAuth SSO | ✅ Complete | PKCE flow, global verifier registry |
| Twitter Posting | ✅ Complete | <150 char summary + URL + hashtags |
| Post Confirmation UI | ✅ Complete | Post/Cancel buttons before publishing |
| LinkedIn SSO | ✅ Complete | PKCE flow, User URN retrieval |
| LinkedIn Posting | ✅ Complete | Directly to member profile |

## 6. Environment Variables

| Variable | Purpose |
|:---------|:--------|
| `PROJECT_ENDPOINT` | Azure AI Foundry endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `MODEL_DEPLOYMENT_NAME` | Model name (e.g., `gpt-4.1-mini`) |
| `SUPADATA_API_KEY` | Supadata transcript API key |
| `TWITTER_CLIENT_ID` | Twitter OAuth2 Client ID |
| `TWITTER_CLIENT_SECRET` | Twitter OAuth2 Client Secret |
| `LINKEDIN_CLIENT_ID` | LinkedIn OAuth2 Client ID |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn OAuth2 Client Secret |
| `OAUTH_REDIRECT_URI` | OAuth callback URL (`http://localhost:8501/`) |
