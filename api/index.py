import os
import sys

# Ensure sih folder is added to sys.path so that internal module imports work seamlessly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
SIH_DIR = os.path.join(ROOT_DIR, 'sih')

if SIH_DIR not in sys.path:
    sys.path.insert(0, SIH_DIR)

# Import the configured Flask application
from app import app

# Export app for Vercel Serverless Function runtime
# Vercel WSGI looks for 'app'
if __name__ == '__main__':
    app.run(debug=True)
