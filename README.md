# YouTube Summarizer Agent

This project is an AI-powered application that automatically generates concise summaries for YouTube videos. It utilizes an agentic workflow to retrieve video transcripts and process them using Large Language Models (LLMs) hosted on Azure.

## Key Features

- **Automated Transcript Extraction**: Uses the `Supadata` API to fetch transcripts from YouTube URLs, supporting auto-detection of languages.
- **Agentic Workflow**: Implements an Azure AI Agent capable of using function tools. The agent intelligently decides when to call the transcript tool based on user input.
- **AI Summarization**: Leverages GPT-4o (via Azure AI Projects) to analyze transcripts and produce easy-to-read summaries of key points.
- **Interactive UI**: Provides a clean web interface using Streamlit for users to input URLs and view results.
- **Real-time Processing**: Handles the orchestration of creating threads, running agents, and streaming responses.
- **Secure Cloud Deployment**: Hosted on Azure App Service using Managed Identity for passwordless authentication and GitHub Actions for CI/CD.

## Tech Stack

### Core Logic & AI

- **Python**: Primary programming language.
- **Azure AI Agent Service**: Manages the agent lifecycle, thread creation, and run orchestration.
- **Azure OpenAI (GPT-4o)**: The underlying model used for reasoning and summarization.
- **Supadata**: External API used as a custom tool for retrieving YouTube video metadata and transcripts.

### Frontend

- **Streamlit**: Used to build the web-based user interface.

### Infrastructure

- **Azure App Service**: Platform for hosting the web application.
- **GitHub Actions**: Automated deployment pipeline.
- **Managed Identity**: Secure, keyless authentication for Azure resources.

### Libraries & SDKs

- `azure-ai-projects`: For interacting with Azure AI Agent resources.
- `azure-identity`: For secure authentication (DefaultAzureCredential).
- `supadata`: Client for the transcript API.
- `python-dotenv`: For managing environment variables.

## Setup & Configuration

### Local Development

1. **Environment Variables**:
   Ensure you have a `.env` file configured with the following:

   - `PROJECT_ENDPOINT`: Your Azure AI Project endpoint.
   - `MODEL_DEPLOYMENT_NAME`: (Optional) The deployment name for the model (defaults to `gpt-4o`).
   - `SUPADATA_API_KEY`: Your Supadata API key.

   _Note: The Supadata API key is currently configured directly in `youtube_tool.py`._

2. **Installation**:
   Install the required dependencies:

   ```bash
   pip install streamlit azure-ai-projects azure-identity supadata python-dotenv
   pip install -r requirements.txt
   ```

3. **Running the App**:
   ```bash
   streamlit run app.py
   ```

### Azure Deployment

1. **Create Web App**:

   - Provision an **Azure App Service** (Linux, Python 3.14).
   - Set the **Startup Command** to: `sh startup.sh`.

2. **Configuration (App Settings)**:
   In the Azure Portal, navigate to **Settings > Environment variables** and add:

   - `PROJECT_ENDPOINT`
   - `SUPADATA_API_KEY`
   - `MODEL_DEPLOYMENT_NAME`

3. **Identity & Permissions**:

   - Enable **System-assigned Managed Identity** for the Web App.
   - Create a **Custom Role** (e.g., "Foundry and Agent Creator") that allows `Microsoft.CognitiveServices/accounts/AIServices/agents/*` actions.
   - Assign this role to the Web App's Managed Identity at the Resource Group or Project level.

4. **CI/CD Pipeline**:
   - Connect your GitHub repository via the **Deployment Center**.
   - Ensure the GitHub Actions workflow is configured for Python 3.14.
