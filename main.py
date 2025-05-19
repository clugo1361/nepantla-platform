import logging
import os
from app import app  # noqa: F401
from api_routes import setup_routes

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Setup API routes
setup_routes(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # ✅ Use Render's assigned port
    app.run(host="0.0.0.0", port=port, debug=True)
