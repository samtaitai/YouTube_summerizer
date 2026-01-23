# System Interface Map: `app.py` (Frontend)

This document outlines the public API surfaces, internal dependencies, and implicit contracts of the Streamlit application layer.

## 1. Public API Surfaces

Since `app.py` serves as the primary UI layer via Streamlit, its "API" is comprised of interactive UI components and state-management helper functions.

| Entry Point | Source File | Input Schema/Event | Return Type | Side Effects |
| :--- | :--- | :--- | :--- | :--- |
| `clear_input()` | `app.py` | UI Button Click (on_click) | `void` | Mutates `st.session_state["youtube_url"]` to an empty string. |
| **Main Script Execution** | `app.py` | Process Start / UI Interaction | `void` | Renders the HTML DOM; triggers Azure AI Agent runs on button click; manages local session state. |

## 2. Internal Dependencies ("Calls-Out")

The module relies on the following external modules and libraries to function:

### Third-Party Libraries
- **`streamlit`**: Used for UI rendering, layout (columns), and session state management.
- **`agent_core.agent_client`**: Specifically imports `summarize_youtube_video`.

### Module-to-Module Contract
- **Service Invocation:** `app.py` assumes that `summarize_youtube_video(url: string)` is a synchronous, blocking call that returns a Markdown-compatible string representing the video summary.
- **Error Handling:** `app.py` wraps the service call in a `try...except` block, assuming that any failure in the backend will raise a catchable `Exception`.

## 3. Data Models

The data flowing through this layer is primarily centered around the user session and the interaction with the backend service.

```typescript
/**
 * Represents the persistent state of the UI during a browser session.
 */
interface StreamlitSessionState {
  youtube_url: string; // The current value in the URL text box
}

/**
 * The expected input for the summarization service.
 */
type YouTubeURL = string;

/**
 * The expected response from the summarization service.
 */
type VideoSummaryResult = string; // Markdown formatted text
```

## 4. Implicit Contracts & Assumptions

- **Streamlit Runtime:** This file **cannot** be run as a standard Python script (`python app.py`) successfully without side effects; it expects to be executed via `streamlit run app.py`.
- **Session State Key Persistence:** The `st.text_input` component is bound to the key `"youtube_url"`. The `clear_input` function assumes this exact key exists in the `st.session_state` dictionary.
- **Blocking Summarization:** The application assumes the user is willing to wait (under a `st.spinner`) while the backend performs the full transcript retrieval and LLM processing. It does not implement an asynchronous or polling architecture at this level.
- **URL Validation:** The code assumes a non-empty string is a potentially valid URL. It relies on the downstream tool (`agent_core`) to perform stricter validation or error out if the URL is malformed.
- **UI Context Manager:** Uses `with col1:` and `with st.spinner:` patterns, assuming the Streamlit context manager logic for layout and UI state properly handles nested elements.
