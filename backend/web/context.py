from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple, Dict

from backend.data_access import (
    _find_default_subject as _find_default_subject_impl,
    discover_subjects_in_file as discover_subjects_in_file_impl,
    get_data_dir as get_data_dir_impl,
    load_participant_data as load_participant_data_impl,
    load_participant_features as load_participant_features_impl,
)


@dataclass
class AppContext:
    """Application context containing configuration and data access methods."""
    base_dir: str
    data_dir_candidates: list[str]
    cache: Any = None
    current_data_dir: Optional[str] = None
    max_full_in_summary: int = 200000

    def get_data_dir(self) -> str:
        """Get the data directory path."""
        return get_data_dir_impl(self.base_dir, self.data_dir_candidates, self.current_data_dir)

    def load_participant_data(self, subject_id: str, allow_unpickle: bool = True) -> Any:
        """Load participant data from disk."""
        return load_participant_data_impl(
            subject_id,
            base_dir=self.base_dir,
            data_dir_candidates=self.data_dir_candidates,
            current_data_dir=self.current_data_dir,
            allow_unpickle=allow_unpickle,
        )

    def load_participant_features(self, subject_id: str) -> Dict[str, Any]:
        """Load participant features from CSV."""
        return load_participant_features_impl(subject_id, self.base_dir)

    def discover_subjects_in_file(self, pkl_path: str) -> list[str]:
        """Discover subject IDs in a pickle file."""
        return discover_subjects_in_file_impl(pkl_path)

    def find_default_subject(self) -> Tuple[Optional[str], Optional[Dict]]:
        """Find a default subject from available files."""
        return _find_default_subject_impl(self.base_dir, self.data_dir_candidates, self.current_data_dir)
