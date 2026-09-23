import os
import sys

# Ensure sih folder is added to sys.path so that internal module imports work seamlessly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
SIH_DIR = os.path.join(ROOT_DIR, 'sih')

if SIH_DIR not in sys.path:
    sys.path.insert(0, SIH_DIR)

# Import the configured Flask application
# pyrefly: ignore [missing-import]
from app import app, index, login

# ==============================================================================
# VERCEL SERVERLESS PATH FIXER MIDDLEWARE
# Solves Vercel internal rewrite PATH_INFO destination rewriting.
# Restores the original matched path from Vercel's edge headers so that
# Flask routes like '/', '/login', '/recommend', and '/static/...' resolve properly.
# ==============================================================================
class VercelPathFixMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Retrieve original path from Vercel edge rewrite headers
        orig_path = (
            environ.get('HTTP_X_MATCHED_PATH') or
            environ.get('HTTP_X_VERCEL_MATCHED_PATH') or
            environ.get('HTTP_X_FORWARDED_URI') or
            environ.get('HTTP_X_ORIGINAL_URL') or
            environ.get('HTTP_X_NOW_ROUTE')
        )

        current_path = environ.get('PATH_INFO', '')

        if orig_path:
            clean = orig_path.split('?')[0]
            # If the header itself was set to /api/index, strip that prefix
            if clean.startswith('/api/index.py'):
                clean = clean[len('/api/index.py'):] or '/'
            elif clean.startswith('/api/index'):
                clean = clean[len('/api/index'):] or '/'
            environ['PATH_INFO'] = clean
        elif current_path.startswith('/api/index.py'):
            environ['PATH_INFO'] = current_path[len('/api/index.py'):] or '/'
        elif current_path.startswith('/api/index'):
            environ['PATH_INFO'] = current_path[len('/api/index'):] or '/'

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

# Explicit fallback routes for direct /api/index requests
@app.route('/api/index', methods=['GET', 'POST'])
@app.route('/api/index.py', methods=['GET', 'POST'])
def vercel_entrypoint_fallback():
    return login()

# Export app for Vercel Serverless Function runtime
if __name__ == '__main__':
    app.run(debug=True)
