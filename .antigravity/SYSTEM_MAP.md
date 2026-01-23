# Workspace System Map: YouTube Summarizer

This document serves as the primary architectural reference for the YouTube Summarizer project.

## 1. Core Architectural Patterns

*   **UI Layer (Streamlit):** Monolithic frontend built with Streamlit (`app.py`). Handles user input, session state, and rendering summaries.
*   **Orchestration (Azure AI Agents):** Decentralized logic using the Azure AI Agents SDK. The system utilizes an "Agent" that manages conversation state (Threads) and autonomous tool invocation.
*   **Decoupled Tooling:** Functional separation of concerns. The `agent_core/youtube_tool.py` acts as an adapter for the Supadata API, keeping business logic separate from AI instructions.
*   **Event-Handler Pattern:** Real-time monitoring and reaction to the Agent's run-cycle through `agent_core/event_handler.py`.

## 2. Primary Data Flow

1.  **Input:** User enters a URL into the Streamlit text field.
2.  **Initialization:** `app.py` triggers `summarize_youtube_video()`.
3.  **Agent Creation:** An AI Project Client is initialized, and a temporary agent is provisioned via Azure AI Foundry.
4.  **Threading:** A unique conversation thread is created for the request.
5.  **Reasoning Loop:**
    *   Agent identifies the need for a transcript based on the user prompt.
    *   Agent requests a "Tool Call" to `get_transcript_text`.
    *   `MyEventHandler` executes the local Python function and sends the output back to the stream.
6.  **External Link:** `Supadata` retrieves transcripts from YouTube.
7.  **Final Synthesis:** The LLM (gpt-4o) summarizes the provided transcript.
8.  **Output:** Streamlit displays the Markdown response.

## 3. Component Breakdown

| File | Responsibility |
| :--- | :--- |
| `app.py` | Entry point, Streamlit UI, top-level error handling. |
| `agent_core/agent_client.py` | Azure AI Client lifecycle, Agent creation/deletion, message polling. |
| `agent_core/youtube_tool.py` | Integration with Supadata API for transcript retrieval. |
| `agent_core/event_handler.py` | Logic for handling streaming events and tool execution during runs. |
| `role.json` | Azure RBAC custom role definition for necessary permissions. |

## 4. Technical Debt & Optimization Roadmap

*   **[Critical] Agent Lifecycle:** Currently creates/deletes an Agent on every request. This adds ~3-5s of latency. *Fix: Use a persistent Agent ID.*
*   **[Medium] Hardcoded Prompts:** Agent instructions are embedded in Python code. *Fix: Move to external config or Azure Foundry definition.*
*   **[Medium] Sync Blocking:** UI blocks during the entire summarization process. *Fix: Implement async processing or Streamlit fragments/callbacks.*
*   **[Low] Persistance:** Threads are abandoned. *Fix: Store Thread IDs in local session storage or a DB to allow "Recent Summaries" feature.*
*   **[Low] Error Handling:** Minimal retry logic for API failures or network timeouts.
