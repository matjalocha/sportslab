"""Feature drift detection using Population Stability Index (PSI).

PSI measures distribution shift between a reference (training) and
current (production) dataset.  Standard interpretation:

- PSI < 0.1  -- no significant shift
- PSI 0.1-0.25 -- noticeable shift (warning)
- PSI > 0.25 -- significant shift requiring investigation (alert)

All functions are pure: no hidden state, no side effects, deterministic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


def compute_psi(
    reference: np.ndarray,
    current: np.ndarray,
    n_bins: int = 10,
    eps: float = 1e-4,
) -> float:
    """Compute PSI between reference and current distributions.

    PSI = sum((current_pct - reference_pct) * ln(current_pct / reference_pct))

    Uses equal-width bins based on the reference distribution range.
    Empty bins are smoothed with *eps* to avoid log(0).

    Args:
        reference: Reference (training) feature values.  Must be non-empty.
        current: Current (production) feature values.  Must be non-empty.
        n_bins: Number of bins for discretization.  Must be >= 2.
        eps: Small constant added to empty bins to ensure numerical stability.

    Returns:
        PSI value.  0 = identical distributions.

    Raises:
        ValueError: If either array is empty or *n_bins* < 2.
    """
    reference = np.asarray(reference, dtype=np.float64).ravel()
    current = np.asarray(current, dtype=np.float64).ravel()

    if len(reference) == 0:
        msg = "reference must not be empty"
        raise ValueError(msg)
    if len(current) == 0:
        msg = "current must not be empty"
        raise ValueError(msg)
    if n_bins < 2:
        msg = "n_bins must be >= 2"
        raise ValueError(msg)

    # Constant reference -- PSI is undefined (zero variance).
    # Return 0.0 when current is also constant at the same value,
    # otherwise return inf to signal a clear distributional break.
    ref_min, ref_max = float(reference.min()), float(reference.max())
    if ref_min == ref_max:
        cur_min, cur_max = float(current.min()), float(current.max())
        if cur_min == cur_max and cur_min == ref_min:
            return 0.0
        return float("inf")

    bin_edges = np.linspace(ref_min, ref_max, n_bins + 1)
    # Extend the last edge slightly so that values equal to ref_max
    # fall into the last bin rather than being clipped out.
    bin_edges[-1] += 1e-10

    ref_counts = np.histogram(reference, bins=bin_edges)[0].astype(np.float64)
    cur_counts = np.histogram(current, bins=bin_edges)[0].astype(np.float64)

    ref_pct = ref_counts / ref_counts.sum()
    cur_pct = cur_counts / cur_counts.sum()

    # Smooth zero-count bins.
    ref_pct = np.where(ref_pct == 0, eps, ref_pct)
    cur_pct = np.where(cur_pct == 0, eps, cur_pct)

    psi = float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))
    return psi


def compute_feature_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: list[str] | None = None,
    n_bins: int = 10,
) -> pd.DataFrame:
    """Compute PSI for multiple features.

    Args:
        reference_df: Reference DataFrame (e.g. training data).
        current_df: Current DataFrame (e.g. recent production data).
        features: Feature columns to check.  ``None`` selects all shared
            numeric columns.
        n_bins: Bins for PSI computation.

    Returns:
        DataFrame with columns ``feature``, ``psi``, ``status``
        (``ok`` / ``warning`` / ``alert``).  Sorted by PSI descending.
    """
    if features is None:
        ref_numeric = set(reference_df.select_dtypes(include="number").columns)
        cur_numeric = set(current_df.select_dtypes(include="number").columns)
        features = sorted(ref_numeric & cur_numeric)

    rows: list[dict[str, object]] = []
    for feature_name in features:
        if feature_name not in reference_df.columns or feature_name not in current_df.columns:
            logger.warning(
                "feature_missing_in_dataframe",
                feature=feature_name,
            )
            continue

        ref_values = reference_df[feature_name].dropna().to_numpy()
        cur_values = current_df[feature_name].dropna().to_numpy()

        if len(ref_values) == 0 or len(cur_values) == 0:
            logger.warning(
                "feature_all_nan",
                feature=feature_name,
            )
            continue

        psi = compute_psi(ref_values, cur_values, n_bins=n_bins)

        if psi > 0.25:
            status = "alert"
        elif psi > 0.1:
            status = "warning"
        else:
            status = "ok"

        rows.append({"feature": feature_name, "psi": psi, "status": status})
        logger.debug(
            "feature_drift_computed",
            feature=feature_name,
            psi=round(psi, 6),
            status=status,
        )

    result = pd.DataFrame(rows, columns=["feature", "psi", "status"])
    return result.sort_values("psi", ascending=False).reset_index(drop=True)


def detect_drift_alerts(
    drift_results: pd.DataFrame,
    warning_threshold: float = 0.1,
    alert_threshold: float = 0.25,
) -> list[dict[str, object]]:
    """Extract features with significant drift.

    Args:
        drift_results: Output of :func:`compute_feature_drift`.
        warning_threshold: PSI above this triggers a warning.
        alert_threshold: PSI above this triggers an alert.

    Returns:
        List of dicts with keys ``feature``, ``psi``, and ``severity``
        (``"warning"`` or ``"alert"``).  Sorted by PSI descending.
    """
    alerts: list[dict[str, object]] = []
    for _, row in drift_results.iterrows():
        psi = float(row["psi"])
        if psi > alert_threshold:
            severity = "alert"
        elif psi > warning_threshold:
            severity = "warning"
        else:
            continue
        alerts.append({
            "feature": row["feature"],
            "psi": psi,
            "severity": severity,
        })

    alerts.sort(key=lambda d: float(str(d["psi"])), reverse=True)
    return alerts
