import os
import re
from html import escape
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware

from fastapi import Request, status
from fastapi.responses import JSONResponse, HTMLResponse

from slowapi import Limiter
from slowapi.util import get_remote_address



limiter = Limiter(key_func=get_remote_address)


class InputValidator:
    @staticmethod
    def sanitize_string(value: Optional[str], max_length: int = 100) -> str:
        """Sanitize and validate string input"""
        if not value:
            return ""
        # Convert to string and strip whitespace
        sanitized = str(value).strip()
        # Escape HTML entities to prevent XSS
        sanitized = escape(sanitized)
        # Enforce length limit
        if len(sanitized) > max_length:
            return ""
        return sanitized
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """Validate username format and content"""
        if not username:
            return False, "Username is required"
        if len(username) < 3:
            return False, "Username too short"
        if len(username) > 50:
            return False, "Username too long"
        # Allow alphanumeric, underscore, dash, dot, @
        if not re.match(r'^[a-zA-Z0-9._@-]+$', username):
            return False, "Invalid username format"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """Validate password format and content"""
        if not password:
            return False, "Password is required"
        if len(password) < 1:
            return False, "Password too short"
        if len(password) > 128:
            return False, "Password too long"
        
        return True, ""


class LoginPasswordMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, protected_paths=None):
        super().__init__(app)
        self.protected_paths = protected_paths or ["/documents"]
    
    async def dispatch(self, request: Request, call_next):
        # Only apply login/password auth to documents paths
        path_requires_login = any(request.url.path.startswith(path) for path in self.protected_paths)
        
        if not path_requires_login:
            return await call_next(request)
        
        auth_token_secret = os.getenv("DOCUMENTS_TOKEN")
        docs_username = os.getenv("DOCUMENTS_USERNAME")
        docs_password = os.getenv("DOCUMENTS_PASSWORD")
        
        if not auth_token_secret:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Server misconfiguration - DOCUMENTS_TOKEN not set"})
        if not docs_username or not docs_password:
            return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Server misconfiguration - DOCUMENTS_USERNAME or DOCUMENTS_PASSWORD not set"})
        
        auth_token = request.cookies.get("auth_token")
        if auth_token and self._verify_token(auth_token, auth_token_secret):
            return await call_next(request)
        
        if request.method == "POST":
            # Rate limiting: 3 login attempts per minute per IP address
            try:
                from limits import parse
                rate_limit = parse("3/minute")
                client_ip = get_remote_address(request)
                if not limiter._limiter.test(rate_limit, client_ip):
                    return self._show_login_form(error="Too many login attempts. Please try again later.")
                limiter._limiter.hit(rate_limit, client_ip)
            except Exception:
                pass
            
            is_secure = request.url.scheme == "https"
            form = await request.form()
            
            raw_username = form.get("username")
            raw_password = form.get("password")
            
            username = InputValidator.sanitize_string(raw_username, max_length=50)
            password = InputValidator.sanitize_string(raw_password, max_length=128)
            
            username_valid, username_error = InputValidator.validate_username(username)
            if not username_valid:
                return self._show_login_form(error=f"Invalid input: {username_error}")
            
            password_valid, password_error = InputValidator.validate_password(password)
            if not password_valid:
                return self._show_login_form(error=f"Invalid input: {password_error}")
            
            # Check credentials (use raw password for comparison to avoid issues with escaping)
            if username == docs_username and raw_password == docs_password:
                response = RedirectResponse(url=str(request.url), status_code=302)
                response.set_cookie(
                    "auth_token", 
                    auth_token_secret,
                    max_age=3600*24*7,
                    httponly=True,
                    secure=is_secure,
                    samesite="strict",
                    path="/documents"
                )
                return response
            else:
                return self._show_login_form(error="Invalid username or password")
        return self._show_login_form()

    @staticmethod
    def _verify_token(token: str, expected_secret: str) -> bool:
        return token == expected_secret

    @staticmethod
    def _show_login_form(error: str = None):
        error_html = ""
        if error:
            # Escape error message to prevent XSS
            escaped_error = escape(str(error))
            error_html = f'<div class="error">{escaped_error}</div>'
        
        login_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Document Access - Recruitee MCP Server</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    max-width: 400px; 
                    margin: 100px auto; 
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h2 {{
                    color: #333;
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .form-group {{ 
                    margin: 20px 0; 
                }}
                label {{
                    display: block;
                    margin-bottom: 5px;
                    color: #555;
                    font-weight: 500;
                }}
                input[type="text"], input[type="password"] {{ 
                    width: 100%; 
                    padding: 12px; 
                    border: 1px solid #ddd; 
                    border-radius: 4px;
                    font-size: 14px;
                    box-sizing: border-box;
                }}
                input[type="text"]:focus, input[type="password"]:focus {{
                    border-color: #007bff;
                    outline: none;
                }}
                button {{ 
                    background: #007bff; 
                    color: white; 
                    padding: 12px 20px; 
                    border: none; 
                    border-radius: 4px; 
                    cursor: pointer;
                    width: 100%;
                    font-size: 16px;
                    margin-top: 10px;
                }}
                button:hover {{ 
                    background: #0056b3; 
                }}
                .error {{
                    background: #f8d7da;
                    color: #721c24;
                    padding: 10px;
                    border-radius: 4px;
                    margin-bottom: 20px;
                    border: 1px solid #f5c6cb;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🔐 Document Access</h2>
                {error_html}
                <form method="post">
                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit">Login</button>
                </form>
                <div class="footer">
                    Recruitee MCP Server - Document Access
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=login_html)
