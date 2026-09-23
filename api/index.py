import os
import sys
from urllib.parse import parse_qs, urlencode

# Ensure sih folder is added to sys.path so that internal module imports work seamlessly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
SIH_DIR = os.path.join(ROOT_DIR, 'sih')

if SIH_DIR not in sys.path:
    sys.path.insert(0, SIH_DIR)

# Import the configured Flask application
# pyrefly: ignore [missing-import]
from app import app

# ==============================================================================
# VERCEL SERVERLESS PATH FIXER MIDDLEWARE
# Solves Vercel internal rewrite routing.
# Maps Vercel rewrite parameter (?path=$1) into Flask's PATH_INFO
# so that all routes ('/', '/login', '/recommend', '/static/...') resolve cleanly.
# ==============================================================================
class VercelPathFixMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string, keep_blank_values=True)

        if 'path' in params:
            val = params['path'][0].strip() if params['path'] else ''
            rewritten = ('/' + val.lstrip('/')) if val else '/'
            environ['PATH_INFO'] = rewritten

            # Remove 'path' query param so Flask application query params remain pure
            remaining_params = {k: v for k, v in params.items() if k != 'path'}
            environ['QUERY_STRING'] = urlencode(remaining_params, doseq=True)
        else:
            path = environ.get('PATH_INFO', '')
            if path in ('/api/index.py', '/api/index', '/api'):
                environ['PATH_INFO'] = '/'

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

# Export app for Vercel Serverless Function runtime
if __name__ == '__main__':
    app.run(debug=True)
