# Pulumi GCP Deployment

This directory contains the Pulumi infrastructure-as-code for deploying the Recruitee MCP Server to Google Cloud Platform.

## Architecture

The deployment uses the following GCP services:
- **Cloud Run**: Serverless container runtime for the MCP server
- **Artifact Registry**: Docker image repository
- **Secret Manager**: Secure storage for API keys and tokens
- **Service Account**: Dedicated identity for the Cloud Run service with least-privilege access

## Prerequisites

1. Install Pulumi CLI:
   ```bash
   curl -fsSL https://get.pulumi.com | sh
   ```

2. Install Python dependencies:
   ```bash
   cd pulumi
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Install and configure Google Cloud SDK:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

4. Configure Docker to authenticate with Artifact Registry:
   ```bash
   gcloud auth configure-docker europe-west2-docker.pkg.dev
   ```

5. Create a GCP project and enable billing

## Configuration

1. Initialize Pulumi stack:
   ```bash
   cd pulumi
   pulumi stack init dev
   ```

2. Configure GCP project:
   ```bash
   pulumi config set gcp:project YOUR_GCP_PROJECT_ID
   pulumi config set gcp:region europe-west2  # Optional, defaults to europe-west2 (London)
   ```

3. Set your secrets in Pulumi config:
   ```bash
   pulumi config set --secret recruitee-mcp-server:recruitee_company_id YOUR_RECRUITEE_COMPANY_ID
   pulumi config set --secret recruitee-mcp-server:recruitee_api_token YOUR_RECRUITEE_API_TOKEN
   ```

4. **Configure OAuth2 authentication (FastMCP OAuth Proxy - REQUIRED):**

   OAuth2 is required for /mcp authentication:

   ```bash
   # Required OAuth2 settings
   pulumi config set --secret recruitee-mcp-server:google_oauth_client_id YOUR_CLIENT_ID
   pulumi config set --secret recruitee-mcp-server:google_oauth_client_secret YOUR_CLIENT_SECRET

   # Optional: Restrict to specific domain (e.g., only allow @yourcompany.com emails)
   pulumi config set recruitee-mcp-server:allowed_oauth_domain yourcompany.com
   ```

   **Note**: FastMCP automatically creates OAuth2 endpoints using BASE_DEPLOY_URL:
   - Authorization: `{BASE_DEPLOY_URL}/authorize`
   - Token: `{BASE_DEPLOY_URL}/token`
   - Callback: `{BASE_DEPLOY_URL}/auth/callback`

   Make sure to configure `{BASE_DEPLOY_URL}/auth/callback` as an authorized redirect URI in your Google Cloud Console OAuth2 credentials.

   **Note**: Pulumi will automatically:
   - Enable required GCP APIs (Secret Manager, Cloud Run, Artifact Registry)
   - Create secrets in GCP Secret Manager
   - Create a dedicated service account for Cloud Run
   - Grant the service account access to the secrets
   - Build and push your Docker image to Artifact Registry

## Deployment

1. Preview the deployment:
   ```bash
   pulumi preview
   ```

2. Deploy to GCP:
   ```bash
   pulumi up
   ```

3. Get the service URL:
   ```bash
   pulumi stack output service_url
   pulumi stack output mcp_endpoint
   ```

## Usage

After deployment, you can connect to your MCP server using OAuth2 authentication.

### Claude.ai Custom Connector

Configure as a custom connector in Claude.ai:

1. Get your service URL:
   ```bash
   pulumi stack output service_url
   ```

2. In Claude.ai, add a custom connector with OAuth2:
   - **Authorization URL**: `https://YOUR_SERVICE_URL/authorize`
   - **Token URL**: `https://YOUR_SERVICE_URL/token`
   - **MCP Endpoint**: `https://YOUR_SERVICE_URL/mcp`

3. Users will authenticate via Google OAuth2 when connecting to the MCP server

## Cleanup

To destroy all resources:
```bash
pulumi destroy
```

## Cost Optimization

The Cloud Run service is configured with:
- Min instances: 0 (scales to zero when not in use)
- Max instances: 10
- CPU: 1 vCPU
- Memory: 512Mi

This configuration keeps costs minimal for development/testing while allowing scale for production use.

## Troubleshooting

### View logs
```bash
gcloud run services logs read recruitee-mcp-server --region europe-west2
```

### Check service status
```bash
gcloud run services describe recruitee-mcp-server --region europe-west2
```

### Update secrets
To update a secret, modify your Pulumi config and run `pulumi up`:
```bash
pulumi config set --secret recruitee-mcp-server:recruitee_api_token NEW_VALUE
pulumi up
```

Alternatively, update directly in GCP and restart your Cloud Run service:
```bash
echo -n "NEW_VALUE" | gcloud secrets versions add SECRET_NAME --data-file=-
gcloud run services update recruitee-mcp-server --region europe-west2
```

## Environment Variables

The following environment variables are configured:

### Required
- `RECRUITEE_COMPANY_ID`: Your Recruitee company ID (from Secret Manager)
- `RECRUITEE_API_TOKEN`: Your Recruitee API token (from Secret Manager)
- `DOCUMENTS_DIR`: Directory for document storage (default: /data/documents)

### Required (OAuth2 - FastMCP OAuth Proxy)
- `GOOGLE_OAUTH_CLIENT_ID`: Google OAuth2 client ID (from Secret Manager)
- `GOOGLE_OAUTH_CLIENT_SECRET`: Google OAuth2 client secret (from Secret Manager)
- `BASE_DEPLOY_URL`: Base URL for the server (plain text, used to construct OAuth redirect URIs)

### Optional (OAuth2)
- `ALLOWED_OAUTH_DOMAIN`: Restrict access to specific Google Workspace domain (plain text)

**Note**: OAuth2 is required for /mcp authentication. FastMCP automatically creates `/authorize`, `/token`, and `/auth/callback` endpoints using the GoogleProvider.
