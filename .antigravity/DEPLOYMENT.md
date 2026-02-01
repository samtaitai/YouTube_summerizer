# Deployment Guide: YouTube Summarizer on Azure App Service

This document provides a complete guide for deploying and updating the YouTube Summarizer application on Azure App Service.

## 1. Prerequisites

Before you begin, ensure you have the following:

*   **Azure CLI** installed and logged in (`az login`).
*   **Git** initialized in the project directory.
*   **Project Source Code** with the latest social posting features.
*   **Resource Group & App Service Name** of your existing deployment.

## 2. Environment Configuration

With the addition of social posting features (Twitter & LinkedIn), you must update the App Service environment variables.

### Required Environment Variables

| Variable | Description |
| :--- | :--- |
| `PROJECT_ENDPOINT` | Azure AI Foundry endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `MODEL_DEPLOYMENT_NAME` | Model name (e.g., `gpt-4.1-mini`) |
| `SUPADATA_API_KEY` | Supadata transcript API key |
| `TWITTER_CLIENT_ID` | Twitter OAuth 2.0 Client ID |
| `TWITTER_CLIENT_SECRET` | Twitter OAuth 2.0 Client Secret |
| `LINKEDIN_CLIENT_ID` | **(New)** LinkedIn OAuth 2.0 Client ID |
| `LINKEDIN_CLIENT_SECRET` | **(New)** LinkedIn OAuth 2.0 Client Secret |
| `OAUTH_REDIRECT_URI` | The production URL callback (e.g., `https://<your-app>.azurewebsites.net/`) |
| `SCM_DO_BUILD_DURING_DEPLOYMENT`| Set to `true` to ensure dependencies are installed. |

### Updating Settings via Azure CLI

Run the following command to bulk-update your app settings. Replace the placeholders with your actual values.

```bash
az webapp config appsettings set --name <APP_NAME> --resource-group <RESOURCE_GROUP> --settings \
  LINKEDIN_CLIENT_ID="<your_linkedin_client_id>" \
  LINKEDIN_CLIENT_SECRET="<your_linkedin_client_secret>" \
  OAUTH_REDIRECT_URI="https://<your-app>.azurewebsites.net/"
```

### Updating Settings via Azure Portal

1.  Log in to the [Azure Portal](https://portal.azure.com).
2.  Navigate to your **App Service** resource.
3.  In the left-hand menu, under **Settings**, select **Environment variables**.
4.  Under the **App settings** tab, click **+ Add** for each of the new variables (`LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, etc.).
5.  Click **Apply** at the bottom, then **Confirm**. The app will automatically restart with the new settings.

## 3. Social Platform Configuration

### Redirect URIs
**Crucial Step:** You must update the "Authorized Redirect URIs" in both your Twitter and LinkedIn Developer Portals to match your production domain.

*   **Format:** `https://<your-app-name>.azurewebsites.net/`
    *   *Note: Streamlit often handles callbacks on the root, but ensure it exactly matches the `OAUTH_REDIRECT_URI` env var.*

## 4. Deployment Steps

Since the application is already deployed, we recommend using `az webapp up` for a streamlined update, or the standard ZIP deploy if you have a specific CI/CD pipeline.

### Option A: Using `az webapp up` (Recommended for Quick Updates)

Run this from the root of your project:

```bash
# Verify you are in the correct directory
ls startup.sh  # Should exist

# Deploy command
az webapp up --name <APP_NAME> --resource-group <RESOURCE_GROUP> --runtime "PYTHON:3.10"
```

*Note: Ensure `startup.sh` is present in the root. Azure App Service for Python uses this file to launch the Streamlit server.*

### Option B: Manual ZIP Deploy

If you need more control or are deploying via a pipeline:

1.  **Build the ZIP archive:**
    ```bash
    zip -r deploy.zip . -x "*.git*" "*.venv*" "__pycache__*" "*.env"
    ```

2.  **Deploy using CLI:**
    ```bash
    az webapp deployment source config-zip --resource-group <RESOURCE_GROUP> \
      --name <APP_NAME> --src deploy.zip
    ```

### Option C: Deploying via Azure Portal (Zip Push)

If you don't want to use the CLI for the actual upload:

1.  **Prepare your ZIP:** Create a `deploy.zip` as described in Option B.
2.  **Access the Kudu Utility:** 
    *   Go to `https://<your-app-name>.scm.azurewebsites.net/ZipDeployUI`.
3.  **Upload:** Drag and drop your `deploy.zip` file directly into the explorer on that page.
4.  Azure will automatically extract the files and trigger the build/restart process.

## 5. Startup Command Verification

Ensure your App Service is configured to run the startup script.

1.  Go to the Azure Portal → Your App Service.
2.  Navigate to **Settings** → **Configuration** → **General Settings**.
3.  Check **Startup Command**. It should be:
    ```bash
    sh startup.sh
    ```
    *(Or explicitly: `python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0`)*

## 6. Post-Deployment Verification

1.  **Navigate to the URL:** `https://<your-app-name>.azurewebsites.net/`
2.  **Check Social Logins:**
    *   Click "Login with LinkedIn".
    *   Verify it redirects to LinkedIn, asks for permissions, and redirects back successfully.
    *   *If you get a generic "Auth Error", double-check the `OAUTH_REDIRECT_URI` match.*
3.  **Test Posting:**
    *   Generate a summary.
    *   Select "LinkedIn" as the platform.
    *   Click "Summarize & Post" to verify the end-to-end flow.
