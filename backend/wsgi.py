"""Production entry point:  gunicorn wsgi:app

Refuses to start without SECRET_KEY, and trusts one proxy hop (Caddy/nginx) for the client address
so the failed-sign-in counter sees real client IPs. Do not expose this app directly to the internet.
"""
import os
import sys

from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app

if not os.environ.get("SECRET_KEY"):
    sys.exit("SECRET_KEY is not set. Generate one with:\n"
             "  python3 -c \"import secrets; print(secrets.token_hex(32))\"")

app = create_app()
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
