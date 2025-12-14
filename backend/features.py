import math
import re
from typing import Any, Dict, Optional

from backend.utils import _rms, _safe_mean

# Stress thresholds
STRESS_THRESHOLDS = {
    "mean_eda": 0.761343,
    "hr": 66.870546,
    "hrv": 325.906461,
    "temp": 31.217497,
    "acc_rms": 1.015106,
}

# Pleasure thresholds
PLEASURE_THRESHOLDS = {
    "mean_eda": 0.557787,
    "hr": 59.803059,
    "hrv": 371.946967,
    "temp": 31.238812,
    "acc_rms": 1.011331,
}

# Neutral ranges
NEUTRAL_RANGES = {
    "mean_eda": (0.557787, 0.761343),
    "hr": (59.803059, 66.870546),
    "hrv": (325.906461, 371.946967),
    "temp": (31.217497, 31.238812),
    "acc_rms": (1.011331, 1.015106),
}


def is_stress(f: Dict[str, Any]) -> bool:
    """Check if features indicate stress state."""
    return (
        (f.get("mean_eda") is not None and f["mean_eda"] > STRESS_THRESHOLDS["mean_eda"])
        or (f.get("hr") is not None and f["hr"] > STRESS_THRESHOLDS["hr"])
        or (f.get("hrv") is not None and f["hrv"] < STRESS_THRESHOLDS["hrv"])
        or (f.get("temp") is not None and f["temp"] < STRESS_THRESHOLDS["temp"])
        or (f.get("acc_rms") is not None and f["acc_rms"] > STRESS_THRESHOLDS["acc_rms"])
    )


def is_pleasure(f: Dict[str, Any]) -> bool:
    """Check if features indicate pleasure state."""
    return (
        (f.get("mean_eda") is not None and f["mean_eda"] < PLEASURE_THRESHOLDS["mean_eda"])
        and (f.get("hr") is not None and f["hr"] < PLEASURE_THRESHOLDS["hr"])
        and (f.get("hrv") is not None and f["hrv"] > PLEASURE_THRESHOLDS["hrv"])
        and (f.get("temp") is not None and f["temp"] > PLEASURE_THRESHOLDS["temp"])
        and (f.get("acc_rms") is not None and f["acc_rms"] < PLEASURE_THRESHOLDS["acc_rms"])
    )


def is_neutral(f: Dict[str, Any]) -> bool:
    """Check if features indicate neutral state."""
    return (
        (f.get("mean_eda") is not None and NEUTRAL_RANGES["mean_eda"][0] <= f["mean_eda"] <= NEUTRAL_RANGES["mean_eda"][1])
        and (f.get("hr") is not None and NEUTRAL_RANGES["hr"][0] <= f["hr"] <= NEUTRAL_RANGES["hr"][1])
        and (f.get("hrv") is not None and NEUTRAL_RANGES["hrv"][0] <= f["hrv"] <= NEUTRAL_RANGES["hrv"][1])
        and (f.get("temp") is not None and NEUTRAL_RANGES["temp"][0] <= f["temp"] <= NEUTRAL_RANGES["temp"][1])
        and (f.get("acc_rms") is not None and NEUTRAL_RANGES["acc_rms"][0] <= f["acc_rms"] <= NEUTRAL_RANGES["acc_rms"][1])
    )


def classify(f: Dict[str, Any]) -> str:
    """Classify emotional state from features."""
    if is_stress(f):
        return "stres"
    if is_pleasure(f):
        return "zadowolenie"
    if is_neutral(f):
        return "neutralny"
    return "nieokreślony"


def _extract_features_from_signals(raw_signals: Any) -> Dict[str, Optional[float]]:
    """Extract features from raw signals with optimized DataFrame handling."""
    features = {
        "mean_eda": None,
        "hr": None,
        "hrv": None,
        "temp": None,
        "acc_rms": None,
    }
    
    try:
        import pandas as pd
    except ImportError:
        pd = None

    # Fast path: DataFrame signals
    if pd is not None and isinstance(raw_signals, pd.DataFrame):
        return _extract_from_dataframe(raw_signals, features)

    # Non-dict signals
    if not isinstance(raw_signals, dict):
        maybe = _safe_mean(raw_signals)
        if maybe is not None and features["mean_eda"] is None:
            features["mean_eda"] = maybe
        return features

    # Dict signals with channel iteration
    return _extract_from_dict_signals(raw_signals, features)


def _extract_from_dataframe(df, features: Dict) -> Dict:
    """Extract features from pandas DataFrame."""
    cols_lower = {c.lower(): c for c in df.columns}
    
    if "eda" in cols_lower:
        features["mean_eda"] = _safe_mean(df[cols_lower["eda"]])
    if "hr" in cols_lower:
        features["hr"] = _safe_mean(df[cols_lower["hr"]])
    
    # HRV calculation
    if "hrv" in cols_lower:
        features["hrv"] = _safe_mean(df[cols_lower["hrv"]])
    elif "rr" in cols_lower:
        features["hrv"] = _calculate_hrv_from_rr(df[cols_lower["rr"]])
    
    if "temp" in cols_lower:
        features["temp"] = _safe_mean(df[cols_lower["temp"]])
    
    # ACC RMS calculation
    acc_candidates = [c for c in df.columns if c.lower().startswith("acc")]
    if acc_candidates:
        features["acc_rms"] = _calculate_acc_rms(df, acc_candidates)
    
    return features


def _calculate_hrv_from_rr(rr_series) -> Optional[float]:
    """Calculate HRV from RR interval series."""
    try:
        seq = [float(x) for x in rr_series if x is not None]
        if len(seq) <= 1:
            return None
        mean = sum(seq) / len(seq)
        variance = sum((x - mean) ** 2 for x in seq) / (len(seq) - 1)
        return math.sqrt(variance)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _calculate_acc_rms(df, acc_candidates) -> Optional[float]:
    """Calculate RMS from acceleration channels."""
    try:
        if len(acc_candidates) > 1:
            return _calculate_multi_axis_rms(df, acc_candidates)
        else:
            return _rms(df[acc_candidates[0]])
    except Exception:
        return None


def _calculate_multi_axis_rms(df, acc_candidates) -> Optional[float]:
    """Calculate RMS from multiple acceleration axes."""
    sq_sum = None
    count_cols = 0
    
    for col in acc_candidates:
        try:
            vals = [float(v) for v in df[col] if v is not None]
        except (TypeError, ValueError):
            vals = []
        
        if not vals:
            continue
        
        if sq_sum is None:
            sq_sum = [0.0] * len(vals)
        
        if len(vals) != len(sq_sum):
            continue
        
        for i, v in enumerate(vals):
            sq_sum[i] += v * v
        count_cols += 1
    
    if sq_sum and count_cols:
        rms_seq = [math.sqrt(x / count_cols) for x in sq_sum]
        return _safe_mean(rms_seq)
    
    return None


def _extract_from_dict_signals(raw_signals: dict, features: Dict) -> Dict:
    """Extract features from dict-based signals."""
    acc_axes = {}
    
    for name, values in _iter_channels(raw_signals):
        lname = (name or "").lower()
        
        # EDA
        if "eda" in lname and features["mean_eda"] is None:
            features["mean_eda"] = _safe_mean(values)
            continue
        
        # HR
        if _is_hr_channel(lname) and features["hr"] is None:
            features["hr"] = _safe_mean(values)
            continue
        
        # HRV
        if "hrv" in lname and features["hrv"] is None:
            features["hrv"] = _safe_mean(values)
            continue
        
        # RR (for HRV calculation)
        if re.search(r"(^|[/:_\-])rr($|[/:_\-])", lname) and features["hrv"] is None:
            features["hrv"] = _calculate_hrv_from_rr(values)
            continue
        
        # Temperature
        if "temp" in lname and features["temp"] is None:
            features["temp"] = _safe_mean(values)
            continue
        
        # Acceleration
        if "acc" in lname:
            _process_acc_channel(values, lname, features, acc_axes)
    
    # Calculate RMS from multiple axes
    if features["acc_rms"] is None and len(acc_axes) >= 2:
        features["acc_rms"] = _calculate_multi_axis_rms_dict(acc_axes)
    
    return features


def _is_hr_channel(lname: str) -> bool:
    """Check if channel is heart rate."""
    return (
        lname == "hr"
        or "/hr" in lname
        or ":hr" in lname
        or "heartrate" in lname
        or lname.endswith("/hr")
    )


def _process_acc_channel(values, lname: str, features: Dict, acc_axes: Dict) -> None:
    """Process acceleration channel."""
    axis = None
    m = re.search(r"acc[^a-z0-9]?([xyz])", lname)
    if m:
        axis = m.group(1)
    
    try:
        seq = list(values) if not hasattr(values, "tolist") else values.tolist()
        seq = [float(x) for x in seq if x is not None]
    except (TypeError, ValueError):
        return
    
    if not seq:
        return
    
    if axis:
        acc_axes[axis] = seq
    elif features["acc_rms"] is None:
        features["acc_rms"] = _rms(seq)


def _calculate_multi_axis_rms_dict(acc_axes: Dict) -> Optional[float]:
    """Calculate RMS from dict of acceleration axes."""
    try:
        L = min(len(v) for v in acc_axes.values() if isinstance(v, list) and v)
        if L <= 0:
            return None
        
        axes = [acc_axes.get(ax) for ax in ("x", "y", "z")]
        axes = [a for a in axes if isinstance(a, list) and a]
        
        if not axes:
            return None
        
        rms_seq = []
        for i in range(L):
            sq_sum = 0.0
            count = 0
            for axis_vals in axes:
                try:
                    v = float(axis_vals[i])
                    sq_sum += v * v
                    count += 1
                except (TypeError, ValueError, IndexError):
                    pass
            
            if count:
                rms_seq.append(math.sqrt(sq_sum / count))
        
        return _safe_mean(rms_seq) if rms_seq else None
    except (TypeError, ValueError):
        return None


def _iter_channels(obj: Any, path: str = ""):
    """Iterate through channels in nested signal structure."""
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        pd = None
        np = None
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}/{k}" if path else str(k)
            yield from _iter_channels(v, new_path)
    else:
        # DataFrame: yield each column
        if pd is not None and isinstance(obj, pd.DataFrame):
            for col in obj.columns:
                yield (f"{path}:{col}", obj[col])
            return
        
        # Series: yield directly
        if pd is not None and isinstance(obj, pd.Series):
            yield (path, obj)
            return
        
        # List/tuple: yield directly
        if isinstance(obj, (list, tuple)):
            yield (path, obj)
            return
        
        # NumPy array: yield directly
        if np is not None and isinstance(obj, np.ndarray):
            yield (path, obj)
            return
        
        # Fallback: wrap in list
        yield (path, [obj])
