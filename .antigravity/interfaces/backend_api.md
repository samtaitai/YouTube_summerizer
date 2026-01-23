# System Interface Map: `agent_core`

This document outlines the public API surfaces, internal dependencies, and implicit contracts of the `agent_core` module.

## 1. Public API Surfaces

The following table summarizes the primary entry points for interacting with the `agent_core` package.

| Entry Point | Source File | Input Schema | Return Type | Side Effects |
| :--- | :--- | :--- | :--- | :--- |
| `summarize_youtube_video(youtube_url: string)` | `agent_client.py` | `{ youtube_url: string }` | `string` (Summary text) | Orchestrates Azure AI Agent creation/deletion; creates persistent Threads; triggers external tool calls. |
| `initialize_agent_client()` | `client.py` | `void` | `AIProjectClient \| None` | Performs Azure Authentication; initializes network connection to Azure AI Projects. |
| `get_transcript_text(youtube_url: string)` | `youtube_tool.py` | `{ youtube_url: string }` | `string` (Transcript text) | Executes HTTP request to Supadata API. |
| `MyEventHandler(functions, client)` | `event_handler.py` | `functions: FunctionTool`, `client: AgentsClient` | `MyEventHandler` (Instance) | Initializes state for event-driven tool execution. |

## 2. Internal Dependencies ("Calls-Out")

The module relies on the following external dependencies and maintains the described "contracts":

### Third-Party Libraries
- **`azure.ai.projects`**: Core orchestration for Agents, Threads, and runs.
- **`azure.identity`**: Provides `DefaultAzureCredential` for secure Azure handshake.
- **`supadata`**: Primary data source for YouTube transcripts.
- **`python-dotenv`**: Lifecycle management for environment variables.

### Module-to-Module Contracts
- **Function Dispatch:** `agent_client.py` registers `get_transcript_text` into a `FunctionTool` definition.
- **Tool Execution:** `MyEventHandler` receives the `FunctionTool` registry and is responsible for calling `functions.execute()` when the Agent status is `requires_action`.
- **Client Hand-off:** `agent_client.py` passes the sub-client `agents_client` to the event handler to allow the handler to submit tool outputs back to the stream.

## 3. Data Models

While the codebase is Python-based (dynamically typed), the logic follows these implicit data shapes:

```typescript
/** 
 * Represents the status of an Azure AI Agent Run step.
 */
type RunStatus = "queued" | "in_progress" | "requires_action" | "completed" | "failed" | "expired" | "cancelled";

/**
 * The output structure expected by the Azure AI Agents SDK after a tool execution.
 */
interface ToolOutput {
  tool_call_id: string; // The unique ID provided by the LLM for this call
  output: string;       // The stringified result of the function execution
}

/**
 * Shape of the tool call request from the LLM.
 */
interface RequiredFunctionToolCall {
  id: string;
  function: {
    name: string;
    arguments: string; // JSON-encoded string
  };
}

/**
 * Response shape for a Thread Message from the Assistant.
 */
interface AssistantResponse {
  role: "assistant";
  text_messages: Array<{
    text: {
      value: string; // The markdown summary content
    }
  }>;
}
```

## 4. Implicit Contracts & Assumptions

- **Environment Variables:** The system assumes the following keys are present in the environment or `.env`:
  - `PROJECT_ENDPOINT`: The Azure AI Project endpoint URL.
  - `SUPADATA_API_KEY`: Authentication for the transcript service.
  - `MODEL_DEPLOYMENT_NAME`: (Optional) Defaults to `gpt-4o`.
- **Pre-Authentication:** `DefaultAzureCredential` expects a valid local identity (e.g., via `az login`) or environment-level Service Principal credentials.
- **Tool-Call Mapping:** `agent_instructions` in `agent_client.py` explicitly directs the LLM to call `get_transcript_text`. Any change to the function name in `youtube_tool.py` must be synchronized with these instructions.
- **Network Access:** Assumes outbound HTTPS access to `*.azure.com` and `api.supadata.ai`.
- **Agent Lifecycle:** The implementation assumes that it is safe to delete the Agent after the summary is generated, even if the Thread persists.
