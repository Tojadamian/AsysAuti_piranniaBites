import os
from typing import Optional

from flask import request

from backend.utils import _parse_bool


def is_unpickle_allowed() -> bool:
    """Check if unpickling is allowed via environment or query parameter."""
    # Check environment variable
    env = _parse_bool(os.environ.get("ALLOW_UNPICKLE"), default=False)
    
    # Check query parameter
    try:
        query_flag = _parse_bool(request.args.get("allow_unpickle"), default=False)
    except RuntimeError:
        query_flag = False
    
    return env or query_flag
