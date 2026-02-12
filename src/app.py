import os
import argparse

import uvicorn
from fastapi.staticfiles import StaticFiles

from src.utils.server_config import mcp, is_oauth_configured
from src.utils.auth import LoginPasswordMiddleware, limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.tools import candidates, offers, lookup, metrics, utils  # noqa: F401
from src.prompts import prompts # noqa: F401



def mount_static_files(app):
    """Helper function to mount static files to the FastAPI app."""
    # Use Fly volume mount path for persistent storage
    documents_dir = os.getenv("DOCUMENTS_DIR") or "./data"
    
    # Ensure the directory exists
    os.makedirs(documents_dir, exist_ok=True)
    
    if os.path.exists(documents_dir):
        app.mount("/documents", StaticFiles(directory=documents_dir), name="documents")
        print(f"Static files mounted at /documents from {documents_dir}")
        return True
    else:
        print(f"Warning: Documents directory not found at {documents_dir}")
        return False


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the Recruitee MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="Transport method for the server (default: stdio)."
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)."
    )
    parser.add_argument(
        "--path",
        required=False,
        help="Mount path for HTTP/SSE (default /mcp or /sse)."
    )

    parser_args = parser.parse_args()

    if parser_args.transport == "sse" and parser_args.path is None:
        parser_args.path = parser_args.path or "/sse"
    elif parser_args.transport == "streamable-http" and parser_args.path is None:
        parser_args.path = parser_args.path or "/mcp"
    else:
        parser_args.path = None
    return parser_args


if __name__ == "__main__":
    if not os.getenv("RECRUITEE_API_TOKEN") or not os.getenv("RECRUITEE_COMPANY_ID"):
        raise SystemExit("Please set RECRUITEE_COMPANY_ID and RECRUITEE_API_TOKEN in your environment variables.")

    args = parse_args()
    if args.transport == "stdio":
        print("Starting MCP server in stdio mode...")
        mcp.run(
            transport=args.transport,
        )

    elif args.transport == "streamable-http":
        print(f"Starting MCP server in streamable-http mode at http://{args.host}:{args.port}{args.path}")
        fastapi_app = mcp.http_app(
            path=args.path,
        )

        # Configure rate limiter
        fastapi_app.state.limiter = limiter
        fastapi_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        # Verify OAuth2 is configured (required for /mcp authentication)
        if not is_oauth_configured():
            raise SystemExit(
                "OAuth2 is required. Please set GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, "
                "and BASE_DEPLOY_URL in your environment variables."
            )

        print("OAuth2 authentication enabled via FastMCP GoogleProvider")
        print("Users will authenticate via Google OAuth2 at /authorize endpoint")
        # FastMCP handles OAuth authentication automatically for /mcp endpoint

        fastapi_app.add_middleware(LoginPasswordMiddleware, protected_paths=["/documents"])
        mount_static_files(fastapi_app)
        uvicorn.run(fastapi_app, host=args.host, port=args.port)

    elif args.transport == "sse":
        print(f"Starting MCP server in SSE mode at http://{args.host}:{args.port}{args.path}")
        mcp.run(
            transport=args.transport,
            path=args.path,
            host=args.host,
            port=args.port,
        )

