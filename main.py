import logging
from app import app  # noqa: F401
from api_routes import setup_routes

# Configure logging for easier debugging
logging.basicConfig(level=logging.DEBUG)

# Setup API routes
setup_routes(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
