from datetime import datetime
from typing import Optional, List

from flask import Blueprint, jsonify, request

from backend.features import classify, STRESS_THRESHOLDS
from backend.utils import _json_error, make_json_safe
from backend.web.context import AppContext
from backend.web.security import is_unpickle_allowed


def create_stress_blueprint(ctx: AppContext) -> Blueprint:
    """Create stress analysis API blueprint."""
    bp = Blueprint("stress", __name__)

    @bp.route("/api/stress_state", methods=["GET"])
    def api_stress_state():
        """Get stress state for a participant."""
        if not is_unpickle_allowed():
            return _json_error(
                "Unpickling jest wyłączony. Ustaw ALLOW_UNPICKLE=1 lub dodaj allow_unpickle=1.",
                status=403
            )

        # Get subject ID
        subject = request.args.get("subject")
        if not subject:
            subject, info = ctx.find_default_subject()
            if not subject:
                return _json_error(
                    "Nie można automatycznie wykryć uczestnika",
                    status=400,
                    info=info
                )

        # Extract numeric subject ID
        subject_id = _extract_subject_id(subject)

        try:
            features = ctx.load_participant_features(subject_id)
        except FileNotFoundError as e:
            return _json_error(str(e), status=404)

        # Classify emotional state
        state = classify(features)
        score = _calculate_stress_score(features)

        result = {
            "subject": f"S{subject_id}",
            "features": features,
            "state": state,
            "score": score,
            "trend": "stabilny",
            "history": [],
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        
        make_json_safe(result)
        return jsonify(result)

    return bp


def _extract_subject_id(subject: str) -> str:
    """Extract numeric subject ID from various formats."""
    if isinstance(subject, str) and subject.upper().startswith("S"):
        numeric = subject[1:]
        if numeric.isdigit():
            return numeric
    return str(subject)


def _calculate_stress_score(features: dict) -> Optional[int]:
    """Calculate stress score based on features."""
    stress_conditions = [
        features.get("mean_eda") is not None and features["mean_eda"] > STRESS_THRESHOLDS["mean_eda"],
        features.get("hr") is not None and features["hr"] > STRESS_THRESHOLDS["hr"],
        features.get("hrv") is not None and features["hrv"] < STRESS_THRESHOLDS["hrv"],
        features.get("temp") is not None and features["temp"] < STRESS_THRESHOLDS["temp"],
        features.get("acc_rms") is not None and features["acc_rms"] > STRESS_THRESHOLDS["acc_rms"],
    ]
    
    known = [c for c in stress_conditions if isinstance(c, bool)]
    if not known:
        return None
    
    stress_count = sum(1 for c in known if c)
    return int(round(100 * stress_count / len(known)))
