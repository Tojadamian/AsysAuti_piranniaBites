import logging
import os
from typing import Optional

from flask import Flask

from backend.web.context import AppContext
from backend.web.routes.chat_routes import create_chat_blueprint
from backend.web.routes.data_routes import create_data_dir_blueprint
from backend.web.routes.home_routes import create_home_blueprint
from backend.web.routes.participant_routes import create_participant_blueprint
from backend.web.routes.stress_routes import create_stress_blueprint

# Configuration constants
DATA_DIR_CANDIDATES = ["S2", "S3"]
MAX_FULL_IN_SUMMARY = 200000
LOG_LEVEL = logging.INFO


def _build_cache():
    """Build cache object if available."""
    try:
        from cache import TTLCache
        return TTLCache(maxsize=256, default_ttl=15.0)
    except ImportError:
        return None


def _enable_env_loading():
    """Load environment variables from .env file."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _enable_cors(app: Flask) -> None:
    """Enable CORS for API endpoints."""
    try:
        from flask_cors import CORS
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    except ImportError:
        pass


def create_app() -> Flask:
    """Create and configure Flask application."""
    # Setup logging
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Get base directory
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Create Flask app
    app = Flask(__name__)

    # Load environment variables and enable CORS
    _enable_env_loading()
    _enable_cors(app)

    # Create application context
    ctx = AppContext(
        base_dir=base_dir,
        data_dir_candidates=DATA_DIR_CANDIDATES,
        cache=_build_cache(),
        current_data_dir=None,
        max_full_in_summary=MAX_FULL_IN_SUMMARY,
    )

    # Register blueprints
    app.register_blueprint(create_home_blueprint())
    app.register_blueprint(create_data_dir_blueprint(ctx))
    app.register_blueprint(create_participant_blueprint(ctx))
    app.register_blueprint(create_stress_blueprint(ctx))
    app.register_blueprint(create_chat_blueprint(ctx))

    return app
