import os

from dotenv import load_dotenv, find_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider



_INSTRUCTIONS = """A server for Recruitee API"""

if find_dotenv() != "":
    load_dotenv(find_dotenv())

RECRUITEE_COMPANY_ID = os.getenv("RECRUITEE_COMPANY_ID")
RECRUITEE_API_TOKEN = os.getenv("RECRUITEE_API_TOKEN")
BASE_DEPLOY_URL = os.getenv("BASE_DEPLOY_URL")

# OAuth2 configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
ALLOWED_OAUTH_DOMAIN = os.getenv("ALLOWED_OAUTH_DOMAIN")

# Check if OAuth is configured
def is_oauth_configured() -> bool:
    """Check if OAuth2 is properly configured"""
    return all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, BASE_DEPLOY_URL])

# Initialize OAuth provider if configured
auth_provider = None
if is_oauth_configured():
    auth_provider = GoogleProvider(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        base_url=BASE_DEPLOY_URL,
        # Note: FastMCP will handle domain validation via the OAuth flow
    )

# Initialize the MCP server with optional OAuth authentication
mcp = FastMCP(
    name="Recruitee Server",
    instructions=_INSTRUCTIONS,
    auth=auth_provider,
)