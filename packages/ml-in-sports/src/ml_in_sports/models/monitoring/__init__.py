"""Production monitoring: feature drift (PSI) and calibration tracking (ECE).

Two submodules:

- :mod:`drift` -- Population Stability Index for detecting feature
  distribution shift between training and production data.
- :mod:`ece` -- Rolling and grouped Expected Calibration Error
  monitoring with alerting.
"""

from ml_in_sports.models.monitoring.drift import (
    compute_feature_drift,
    compute_psi,
    detect_drift_alerts,
)
from ml_in_sports.models.monitoring.ece import (
    compute_ece_per_group,
    compute_rolling_ece,
    ece_alert,
)

__all__ = [
    "compute_ece_per_group",
    "compute_feature_drift",
    "compute_psi",
    "compute_rolling_ece",
    "detect_drift_alerts",
    "ece_alert",
]
