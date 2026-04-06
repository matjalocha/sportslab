"""Ensemble models: registry, wrappers, and stacking meta-learner.

Provides a unified :class:`PredictionModel` protocol and concrete
wrappers for LightGBM, XGBoost, TabPFN, plus a
:class:`StackingEnsemble` that combines base model OOF predictions
via a logistic regression meta-learner.

Usage::

    from ml_in_sports.models.ensemble import create_model, StackingEnsemble

    lgb = create_model("lightgbm", n_estimators=200)
    xgb = create_model("xgboost", n_estimators=200)
    ensemble = StackingEnsemble(base_models=[lgb, xgb])
    ensemble.fit(X_train, y_train)
    probs = ensemble.predict_proba(X_test)
"""

from ml_in_sports.models.ensemble.registry import (
    MODEL_REGISTRY,
    DummyModel,
    LightGBMModel,
    PredictionModel,
    TabPFNModel,
    XGBoostModel,
    create_model,
)
from ml_in_sports.models.ensemble.stacking import StackingEnsemble

__all__ = [
    "MODEL_REGISTRY",
    "DummyModel",
    "LightGBMModel",
    "PredictionModel",
    "StackingEnsemble",
    "TabPFNModel",
    "XGBoostModel",
    "create_model",
]
