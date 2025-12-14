import os
from typing import List

from flask import Blueprint, jsonify, request

from backend.utils import _json_error
from backend.web.context import AppContext


def create_data_dir_blueprint(ctx: AppContext) -> Blueprint:
    """Create data directory management API blueprint."""
    bp = Blueprint("data_dir", __name__)

    @bp.route("/data_dir", methods=["GET"])
    def data_dir_info():
        """Get current data directory and file listing."""
        data_param = request.args.get("dir")

        # Handle directory parameter
        if data_param:
            try:
                _set_data_dir(ctx, data_param)
            except ValueError as e:
                return _json_error(str(e), status=400)

        data_dir = ctx.get_data_dir()

        # Get file listing with caching
        files = _get_files_cached(ctx, data_dir)
        
        return jsonify({"data_dir": data_dir, "files": files})

    return bp


def _set_data_dir(ctx: AppContext, dir_param: str) -> None:
    """Set or reset the current data directory."""
    if dir_param.lower() in ("auto", "reset", ""):
        ctx.current_data_dir = None
        return

    # Resolve candidate path
    candidate = dir_param if os.path.isabs(dir_param) else os.path.join(ctx.base_dir, dir_param)
    
    # Fallback to absolute path if provided
    if not os.path.isdir(candidate) and os.path.isdir(dir_param):
        candidate = dir_param
    
    # Validate directory exists
    if not os.path.isdir(candidate):
        raise ValueError(f"Katalog nie istnieje: {dir_param}")
    
    ctx.current_data_dir = candidate


def _get_files_cached(ctx: AppContext, data_dir: str) -> List[str]:
    """Get file listing with caching support."""
    def _list_files():
        if os.path.isdir(data_dir):
            return sorted(os.listdir(data_dir))
        return []

    if ctx.cache:
        return ctx.cache.get_or_set(f"dir_list:{data_dir}", _list_files, ttl=10.0)
    else:
        return _list_files()
