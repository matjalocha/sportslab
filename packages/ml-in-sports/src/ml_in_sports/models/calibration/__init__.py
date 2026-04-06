"""Calibration scalers for post-hoc probability calibration.

Three methods are provided:

- :class:`TemperatureScaler` -- single-parameter temperature scaling,
  best for uniformly overconfident models (e.g. TabPFN).
- :class:`PlattScaler` -- logistic regression on logits (Platt 1999),
  good general-purpose parametric calibration.
- :class:`IsotonicScaler` -- non-parametric isotonic regression, most
  flexible but requires more validation data.

The :class:`CalibrationSelector` auto-picks the best method via
walk-forward cross-validation on ECE.

All scalers support both binary (over/under, BTTS) and multiclass
(1X2: home/draw/away) predictions.
"""

from ml_in_sports.models.calibration.isotonic import IsotonicScaler
from ml_in_sports.models.calibration.platt import PlattScaler
from ml_in_sports.models.calibration.selector import (
    CalibrationSelector,
    Calibrator,
    _compute_ece,
)
from ml_in_sports.models.calibration.temperature import TemperatureScaler

__all__ = [
    "CalibrationSelector",
    "Calibrator",
    "IsotonicScaler",
    "PlattScaler",
    "TemperatureScaler",
    "_compute_ece",
]
