# Recruitee MCP Server

**Model Context Protocol (MCP) server for Recruitee – advanced search, reporting, and analytics for recruitment data.**

[![Deploy on Fly.io](https://badgen.net/badge/Fly.io/deploy/green)](https://fly.io/apps/recruitee-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Overview

The **Model Context Protocol (MCP)** is rapidly becoming the standard for connecting AI agents to external services. This project implements an MCP server for [Recruitee](https://recruitee.com/), enabling advanced, AI-powered search, filtering, and reporting on recruitment data.

Unlike basic CRUD wrappers, this server focuses on the tasks where LLMs and AI agents excel: **summarizing, searching, and filtering**. It exposes a set of tools and prompt templates, making it easy for any MCP-compatible client to interact with Recruitee data in a structured, agent-friendly way.

---

## ✨ Features

* [x] **Advanced Candidate Search & Filtering**  
  Search for candidates by skills, status, talent pool, job, tags, and more. Example:  
  _"Find candidates with Elixir experience who were rejected due to salary expectations."_

* [x] **Recruitment Summary Reports**  
  Generate summaries of recruitment activities, such as time spent in each stage, total process duration, and stage-by-stage breakdowns.

* [x] **Recruitment Statistics**  
  Calculate averages and metrics (e.g., average expected salary for backend roles, average time to hire, contract type stats).

* [x] **General Search**  
  Quickly find candidates, recruitments, or talent pools by name or attribute.

* [x] **Prompt Templates**  
  Exposes prompt templates for LLM-based clients, ensuring consistent and high-quality summaries.

---

## 🛠 Example Queries

- _Find candidates with Elixir experience who were rejected due to salary expectations._
- _Show me their personal details including CV URL._
- _Why was candidate 'X' disqualified and at what stage?_
- _What are the other stages for this offer?_
- _Show candidates whose GDPR certification expires this month._
- _What's time to fill sales assistant offer?_
- _Create a pie chart with sources for AI engineer offer._
- _Create a recruitment report._

---

## 🧑‍💻 Implementation

- **Language:** Python
- **Framework:** [FastMCP](https://github.com/chrishayuk/fastmcp)
- **API:** [Recruitee Careers Site API](https://docs.recruitee.com/reference/intro-to-careers-site-api)
- **Schemas:** All MCP tool schemas are generated from Pydantic models, with rich metadata for LLMs.

The server retrieves and processes data from Recruitee, exposing it via MCP tools. Summaries are composed by the client using provided prompt templates.

---

## 🔐 Authentication

The server supports three authentication methods for the `/mcp` endpoint:

### 1. **Google OAuth2** (Recommended for Teams)

The most secure option for team deployments. Users authenticate via their Google accounts.

**Setup:**

1. **Create OAuth2 credentials in Google Cloud Console:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - Add authorized redirect URI: `{BASE_DEPLOY_URL}/auth/callback`
     - Example: `https://recruitee-mcp-server.run.app/auth/callback`
   - Copy the **Client ID** and **Client Secret**

2. **Configure environment variables:**
   ```bash
   BASE_DEPLOY_URL=https://your-server.run.app
   GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
   ```

3. **Optional - Restrict access by domain:**
   ```bash
   ALLOWED_OAUTH_DOMAIN=yourcompany.com  # Only allow @yourcompany.com emails
   ```

**FastMCP OAuth Proxy Endpoints:**

FastMCP automatically creates these OAuth2 endpoints:
- Authorization: `{BASE_DEPLOY_URL}/authorize`
- Token: `{BASE_DEPLOY_URL}/token`
- Callback: `{BASE_DEPLOY_URL}/auth/callback`

**Usage:**
- Users authenticate via Google OAuth2 at the `/authorize` endpoint
- Compatible with Claude.ai custom connectors and MCP clients
- Access tokens are issued via the `/token` endpoint
- Sessions are managed by FastMCP's OAuth proxy

**Note:** OAuth2 is required for /mcp authentication. Your Recruitee API credentials remain securely stored server-side in environment variables.

---

## 🚦 Transport Methods

- **stdio** – For local development and testing.
- **streamable-http** – For remote, production-grade deployments (recommended).
- **SSE** – Supported but deprecated in some MCP frameworks.

---

## 🧪 Usage

### For Claude.ai Teams (Recommended)

The easiest way to use this MCP server is through Claude.ai's custom connectors. No installation required for end users!

#### Admin Setup (One-time)

1. **Navigate to Admin Settings**
   - Go to your Claude.ai organization settings
   - Click on **Admin** → **Connectors**

2. **Add Custom Connector with OAuth2**
   - Click **"Add custom connector"** at the bottom of the page
   - Fill in the following details:

   | Field | Value |
   |-------|-------|
   | **Name** | `Recruitee` |
   | **Remote MCP Server URL** | `https://your-server-url.run.app/mcp` |
   | **OAuth Authorization URL** | `https://your-server-url.run.app/authorize` |
   | **OAuth Token URL** | `https://your-server-url.run.app/token` |
   | **OAuth Client ID** | Your Google OAuth Client ID |
   | **OAuth Client Secret** | Your Google OAuth Client Secret |

   > **Note:** Update the server URL to match your deployment. Users will authenticate via Google OAuth2.

3. **Save**
   - Click **"Add"** to save the connector

#### User Setup (Each Team Member)

Once the admin has added the connector:

1. Go to your Claude.ai settings
2. Navigate to **Connectors**
3. Find **Recruitee** in the available connectors list
4. Click to **enable** it
5. Start using it immediately in any conversation!

**No Node.js installation or technical setup required** - it works directly in the Claude.ai web interface.

---

### For Local Development (stdio)

For testing and development purposes:

1. **Configure your MCP client:**

    ```json
    {
      "mcpServers": {
        "recruitee": {
          "command": "/path/to/.venv/bin/python",
          "args": ["/path/to/recruitee-mcp-server/src/app.py", "--transport", "stdio"]
        }
      }
    }
    ```

2. **Run with [mcp-cli](https://github.com/chrishayuk/mcp-cli):**

    ```bash
    mcp-cli chat --server recruitee --config-file /path/to/mcp-cli/server_config.json
    ```

---

### For Claude Desktop (Advanced)

If you prefer to use Claude Desktop app with Node.js installed:

```json
{
  "mcpServers": {
    "recruitee": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/recruitee-mcp-server",
        "run",
        "python",
        "-m",
        "src.app"
      ]
    }
  }
}
```

**Note:** For local development, use stdio mode instead of the remote server. The remote server requires OAuth2 authentication which is designed for web-based clients like Claude.ai custom connectors.

💡 **Tip:** For data visualization, combine this with chart-specific MCP servers like [mcp-server-chart](https://github.com/antvis/mcp-server-chart)

---

## ☁️ Deployment

### Deploy to Google Cloud Platform (GCP)

This project includes a Pulumi setup for easy deployment to GCP Cloud Run.

#### Prerequisites

- Google Cloud account with billing enabled
- [Pulumi](https://www.pulumi.com/docs/get-started/install/) installed
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated

#### Deployment Steps

1. **Authenticate with GCP:**
   ```bash
   gcloud auth application-default login
   gcloud auth configure-docker europe-west2-docker.pkg.dev
   ```

2. **Configure Pulumi secrets:**
   ```bash
   cd pulumi
   pulumi config set recruitee-api-token YOUR_RECRUITEE_API_TOKEN --secret
   pulumi config set recruitee-company-id YOUR_COMPANY_ID --secret
   pulumi config set documents-token YOUR_DOCS_TOKEN --secret
   pulumi config set documents-username YOUR_USERNAME --secret
   pulumi config set documents-password YOUR_PASSWORD --secret

   # Optional: Configure OAuth2 (recommended for team deployments)
   pulumi config set google-oauth-client-id YOUR_CLIENT_ID --secret
   pulumi config set google-oauth-client-secret YOUR_CLIENT_SECRET --secret
   pulumi config set google-oauth-redirect-uri https://your-server.run.app/auth/google/callback
   pulumi config set oauth-session-secret YOUR_SESSION_SECRET --secret
   # Optional: Restrict to specific domain or emails
   pulumi config set allowed-oauth-domain yourcompany.com
   # pulumi config set allowed-oauth-emails alice@example.com,bob@example.com
   ```

3. **Deploy:**
   ```bash
   pulumi up
   ```

4. **Get your server URL:**
   After deployment, Pulumi will output your server URL (e.g., `https://recruitee-mcp-server-xxx.a.run.app`)

5. **Use in Claude.ai:**
   Configure the custom connector with OAuth2 (see "Usage with Claude.ai Teams" section above for detailed setup instructions)

---

### Deploy to Fly.io (Alternative)

1. **Set your secrets in `.env`**
2. **Create a volume:**
    ```bash
    make create_volume
    ```
3. **Deploy:**
    ```bash
    flyctl auth login
    make deploy
    ```

---

## 📚 Resources

- [Recruitee MCP Server (GitHub)](https://github.com/EmpoweredHouse/recruitee-mcp-server)
- [Recruitee API Docs](https://docs.recruitee.com/reference/intro-to-careers-site-api)
- [Model Context Protocol (MCP)](https://github.com/chrishayuk/model-context-protocol)
- [FastMCP Framework](https://github.com/chrishayuk/fastmcp)
- [MCP Server for Charts](https://github.com/antvis/mcp-server-chart)
---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!  

---

## 📝 License

This project is [MIT licensed](LICENSE).

---

**Empower your AI agents with advanced recruitment data access and analytics.**

