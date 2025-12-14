import json
import math
import os
from typing import Any, Dict, Optional

import numpy as np
from flask import jsonify


def _parse_bool(value: Any, default: bool = False) -> bool:
    """Parse a value to boolean efficiently."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: Any, default: int) -> int:
    """Parse a value to int with fallback."""
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json_error(message: str, status: int = 400, **extra) -> tuple:
    """Create a JSON error response."""
    payload = {"error": message, **extra}
    return jsonify(payload), status


def make_json_safe(d: Dict[str, Any]) -> None:
    """Recursively remove NaN and Inf values from dict."""
    for k, v in d.items():
        if isinstance(v, dict):
            make_json_safe(v)
        elif isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            d[k] = None


def _safe_mean(seq: Any) -> Optional[float]:
    """Calculate mean safely, handling various input types."""
    if seq is None:
        return None
    
    try:
        # Convert to list if needed
        if hasattr(seq, "tolist"):
            seq = seq.tolist()
        
        # Filter numeric values
        vals = [float(x) for x in seq if x is not None]
        if not vals:
            return None
        
        # Use built-in sum for efficiency
        return sum(vals) / len(vals)
    except (TypeError, ValueError):
        return None


def _rms(seq: Any) -> Optional[float]:
    """Calculate RMS (root mean square) safely."""
    if seq is None:
        return None
    
    try:
        # Convert to list if needed
        if hasattr(seq, "tolist"):
            seq = seq.tolist()
        
        # Filter numeric values
        vals = [float(x) for x in seq if x is not None]
        if not vals:
            return None
        
        # Efficient RMS calculation
        mean_sq = sum(x * x for x in vals) / len(vals)
        return math.sqrt(mean_sq)
    except (TypeError, ValueError):
        return None


def _summarize_object(obj: Any, n: int = 20, include_full: bool = False, max_full: int = 100000) -> Dict:
    """Summarize any object for API response."""
    try:
        import pandas as pd
        import numpy as np_lib
    except ImportError:
        pd = None
        np_lib = None

    summary = {"type": type(obj).__name__}

    # Handle pandas Series
    if pd is not None and isinstance(obj, pd.Series):
        length = len(obj)
        summary.update({"length": int(length), "dtype": str(obj.dtype)})
        try:
            summary["sample"] = obj.iloc[:n].tolist()
        except (ValueError, TypeError):
            summary["sample"] = list(obj.iloc[:n].astype(str))
        
        if include_full and length <= max_full:
            try:
                summary["full"] = obj.tolist()
            except (ValueError, TypeError):
                pass
        return summary

    # Handle pandas DataFrame
    if pd is not None and isinstance(obj, pd.DataFrame):
        length = len(obj)
        summary.update({"length": int(length), "columns": list(obj.columns)})
        try:
            summary["sample_rows"] = obj.head(n).to_dict(orient="records")
        except (ValueError, TypeError):
            summary["sample_rows"] = []
        
        if include_full and length <= max_full:
            try:
                summary["full_rows"] = obj.to_dict(orient="records")
            except (ValueError, TypeError):
                pass
        return summary

    # Handle numpy arrays
    if np_lib is not None and isinstance(obj, np_lib.ndarray):
        length = obj.size
        summary.update({"length": int(length), "dtype": str(obj.dtype)})
        try:
            summary["sample"] = obj.flatten()[:n].tolist()
        except (ValueError, TypeError):
            summary["sample"] = []
        
        if include_full and length <= max_full:
            try:
                summary["full"] = obj.flatten().tolist()
            except (ValueError, TypeError):
                pass
        return summary

    # Handle list/tuple
    if isinstance(obj, (list, tuple)):
        length = len(obj)
        summary.update({"length": int(length)})
        try:
            summary["sample"] = [
                x if isinstance(x, (int, float, str, bool, type(None))) else str(x)
                for x in list(obj)[:n]
            ]
        except (TypeError, ValueError):
            summary["sample"] = []
        
        if include_full and length <= max_full:
            try:
                summary["full"] = [
                    x if isinstance(x, (int, float, str, bool, type(None))) else str(x)
                    for x in list(obj)
                ]
            except (TypeError, ValueError):
                pass
        return summary

    # Generic handling
    try:
        length = len(obj)
        summary.update({"length": int(length)})
    except (TypeError, AttributeError):
        summary.update({"length": None})

    try:
        s = obj[:n]
        try:
            summary["sample"] = s.tolist()
        except (ValueError, AttributeError):
            summary["sample"] = [str(x) for x in s]
    except (TypeError, IndexError):
        try:
            summary["sample"] = [obj]
        except (TypeError, ValueError):
            summary["sample"] = [str(obj)]

    return summary
