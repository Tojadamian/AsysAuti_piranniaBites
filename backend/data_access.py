import glob
import logging
import os
import pickle
import re
from functools import lru_cache
from typing import Optional, Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def get_data_dir(base_dir: str, data_dir_candidates: List[str], current_data_dir: Optional[str]) -> str:
    """Get the data directory with caching and efficient path resolution."""
    if current_data_dir and os.path.isdir(current_data_dir):
        return current_data_dir
    
    # Check all candidates efficiently
    for candidate in data_dir_candidates:
        # Absolute path check
        if os.path.isabs(candidate) and os.path.isdir(candidate):
            return candidate
        # Relative path check
        relative = os.path.join(base_dir, candidate)
        if os.path.isdir(relative):
            return relative
        # Direct check
        if os.path.isdir(candidate):
            return candidate
    
    # Return default fallback
    return os.path.join(base_dir, data_dir_candidates[0])


def _safe_pickle_load(f, allow_unpickle: bool = True):
    """Load pickle with proper error handling and encoding fallbacks."""
    if not allow_unpickle:
        raise RuntimeError(
            "Unpickling disabled (allow_unpickle=False). Set ALLOW_UNPICKLE=1 or pass allow_unpickle=1 in query params to enable loading pickli."
        )
    
    # Try primary encoding first
    try:
        return pickle.load(f)
    except (UnicodeDecodeError, ValueError, pickle.UnpicklingError):
        # Fallback to latin1 encoding
        f.seek(0)
        try:
            return pickle.load(f, encoding="latin1")
        except (TypeError, EOFError):
            # Final attempt with bytes encoding
            f.seek(0)
            return pickle.load(f)


def load_participant_features(subject_id: str, base_dir: str) -> Dict[str, any]:
    """Load participant features from CSV with efficient error handling."""
    csv_path = os.path.join(base_dir, "data", f"S{subject_id}.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV for subject S{subject_id} not found")

    df = pd.read_csv(csv_path, dtype={
        "mean_eda": "float32",
        "temp": "float32", 
        "emg": "float32",
        "acc_rms": "float32",
        "hr": "float32",
        "hrv": "float32"
    })
    
    subj_rows = df[df["subject"] == f"S{subject_id}"]
    if subj_rows.empty:
        raise ValueError(f"No data for subject S{subject_id}")

    row = subj_rows.iloc[0]
    features = {
        "mean_eda": float(row["mean_eda"]),
        "temp": float(row["temp"]),
        "emg": float(row["emg"]) if pd.notna(row["emg"]) else 0.0,
        "acc_rms": float(row["acc_rms"]),
        "hr": float(row["hr"]),
        "hrv": float(row["hrv"]),
        "state": str(row["state"]),
    }
    logger.debug("Loaded features for subject %s", subject_id)
    return features


def load_participant_data(
    subject_id: str,
    base_dir: str,
    data_dir_candidates: List[str],
    current_data_dir: Optional[str],
    allow_unpickle: bool = True
):
    """Load participant data with optimized path resolution."""
    data_dir = get_data_dir(base_dir, data_dir_candidates, current_data_dir)
    target_name = f"S{subject_id}"

    # First, try direct file match
    pkl_path = os.path.join(data_dir, f"{target_name}.pkl")
    if os.path.exists(pkl_path):
        with open(pkl_path, "rb") as f:
            return _safe_pickle_load(f, allow_unpickle=allow_unpickle)

    # Then try glob match
    matches = glob.glob(os.path.join(data_dir, f"{target_name}*.pkl"))
    if matches:
        with open(matches[0], "rb") as f:
            return _safe_pickle_load(f, allow_unpickle=allow_unpickle)

    # Try CSV as fallback
    csv_path = os.path.join(data_dir, f"{target_name}.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df.to_pickle(pkl_path)
        return df

    # Search in alternative directories
    for candidate in data_dir_candidates:
        cand_path = candidate if os.path.isabs(candidate) else os.path.join(base_dir, candidate)
        try:
            if os.path.abspath(cand_path) == os.path.abspath(data_dir):
                continue
        except Exception:
            continue
            
        if not os.path.isdir(cand_path):
            continue
            
        alt_pkl = os.path.join(cand_path, f"{target_name}.pkl")
        if os.path.exists(alt_pkl):
            with open(alt_pkl, "rb") as f:
                return _safe_pickle_load(f, allow_unpickle=allow_unpickle)
        
        alt_matches = glob.glob(os.path.join(cand_path, f"{target_name}*.pkl"))
        if alt_matches:
            with open(alt_matches[0], "rb") as f:
                return _safe_pickle_load(f, allow_unpickle=allow_unpickle)

    # Last resort: search all pkl files
    all_pkls = glob.glob(os.path.join(data_dir, "*.pkl"))
    if not all_pkls:
        dir_contents = os.listdir(data_dir) if os.path.isdir(data_dir) else "brak katalogu"
        raise FileNotFoundError(f"Brak plików .pkl w katalogu danych. Zawartość: {dir_contents}")

    with open(all_pkls[0], "rb") as f:
        container = _safe_pickle_load(f, allow_unpickle=allow_unpickle)

    # Extract from container efficiently
    result = _extract_from_container(container, target_name, subject_id, all_pkls)
    if result is not None:
        return result
    
    raise FileNotFoundError(f"Nie znaleziono danych dla {target_name}")


def _extract_from_container(container, target_name: str, subject_id: str, all_pkls: List[str]):
    """Extract target data from various container formats."""
    # Direct dict lookup
    if isinstance(container, dict):
        if target_name in container:
            return container[target_name]
        if str(subject_id) in container:
            return container[str(subject_id)]
        
        # Search for matching dict entries
        for k, v in container.items():
            try:
                if isinstance(v, dict) and v.get("subject") in (target_name, subject_id, str(subject_id)):
                    return v
            except Exception:
                continue

    # Handle list/tuple containers
    if isinstance(container, (list, tuple)):
        for item in container:
            try:
                if isinstance(item, dict) and item.get("subject") in (target_name, subject_id, str(subject_id)):
                    return item
            except Exception:
                continue

    # Handle DataFrame containers
    try:
        if isinstance(container, pd.DataFrame):
            if "subject" in container.columns:
                sel = container[container["subject"].isin([target_name, subject_id, str(subject_id)])]
                if not sel.empty:
                    return sel
    except Exception:
        pass

    return None


def discover_subjects_in_file(pkl_path: str) -> List[str]:
    """Discover subjects in a pickle file efficiently."""
    subjects = set()
    
    with open(pkl_path, "rb") as f:
        try:
            container = _safe_pickle_load(f)
        except Exception as e:
            raise RuntimeError(f"Błąd ładowania {os.path.basename(pkl_path)}: {e}")

    # Handle single-subject dict
    if isinstance(container, dict) and "subject" in container:
        s = container.get("subject")
        if s is not None:
            return [str(s)]

    # Search dict keys
    if isinstance(container, dict):
        _extract_subjects_from_dict_keys(container, subjects)
        _extract_subjects_from_dict_values(container, subjects)

    # Search list/tuple items
    if isinstance(container, (list, tuple)):
        for item in container:
            try:
                if isinstance(item, dict):
                    s = item.get("subject")
                    if s is not None:
                        subjects.add(str(s))
            except Exception:
                pass

    # Search DataFrame
    _extract_subjects_from_dataframe(container, subjects)

    return sorted(subjects)


def _extract_subjects_from_dict_keys(container: dict, subjects: set):
    """Extract subject IDs from dict keys."""
    for k in container.keys():
        try:
            ks = str(k)
            if re.match(r"^[sS]\d+$", ks):
                subjects.add(ks.upper())
            elif re.match(r"^\d+$", ks):
                subjects.add(f"S{ks}")
        except Exception:
            pass


def _extract_subjects_from_dict_values(container: dict, subjects: set):
    """Extract subject IDs from dict values."""
    for v in container.values():
        try:
            if isinstance(v, dict):
                s = v.get("subject")
                if s is not None:
                    subjects.add(str(s))
        except Exception:
            pass


def _extract_subjects_from_dataframe(container, subjects: set):
    """Extract subject IDs from DataFrame."""
    try:
        if isinstance(container, pd.DataFrame):
            if "subject" in container.columns:
                vals = container["subject"].unique().tolist()
                for v in vals:
                    subjects.add(str(v))
    except Exception:
        pass


def _find_default_subject(
    base_dir: str,
    data_dir_candidates: List[str],
    current_data_dir: Optional[str]
) -> Tuple[Optional[str], Optional[Dict]]:
    """Find a default subject from available pickle files."""
    data_dir = get_data_dir(base_dir, data_dir_candidates, current_data_dir)
    if not os.path.isdir(data_dir):
        return None, "Katalog danych nie istnieje"
    
    pkls = glob.glob(os.path.join(data_dir, "*.pkl"))
    if not pkls:
        return None, "Brak plików .pkl w katalogu"

    subjects = set()
    subjects_by_file = {}
    
    for pkl_file in pkls:
        try:
            subs = discover_subjects_in_file(pkl_file)
        except Exception:
            subs = []
        
        subjects_by_file[os.path.basename(pkl_file)] = subs
        subjects.update(subs)

    # Return if single subject found
    if len(subjects) == 1:
        return next(iter(subjects)), None

    # Fallback to filename if no subjects
    if not subjects and len(pkls) == 1:
        fn = os.path.splitext(os.path.basename(pkls[0]))[0]
        if fn:
            return fn, None

    return None, {"note": "wiele_subjectów", "subjects_by_file": subjects_by_file}
