"""Tests for experiment configuration parsing and validation."""

from pathlib import Path

import pytest
from ml_in_sports.backtesting.config import (
    CalibrationConfig,
    DataConfig,
    ExperimentConfig,
    KellyConfig,
    ModelConfig,
)


class TestModelConfig:
    """Tests for ModelConfig validation."""

    def test_basic_model(self) -> None:
        """Simple model config is valid."""
        m = ModelConfig(name="lgb", type="lightgbm")
        assert m.name == "lgb"
        assert m.type == "lightgbm"

    def test_stacking_requires_base_models(self) -> None:
        """Stacking without base_models raises."""
        with pytest.raises(ValueError, match="base_models"):
            ModelConfig(name="stack", type="stacking")

    def test_stacking_requires_meta_learner(self) -> None:
        """Stacking without meta_learner raises."""
        with pytest.raises(ValueError, match="meta_learner"):
            ModelConfig(
                name="stack",
                type="stacking",
                base_models=["lgb", "xgb"],
            )

    def test_stacking_valid(self) -> None:
        """Valid stacking config passes."""
        m = ModelConfig(
            name="stack",
            type="stacking",
            base_models=["lgb", "xgb"],
            meta_learner="logistic_regression",
        )
        assert m.base_models == ["lgb", "xgb"]


class TestKellyConfig:
    """Tests for Kelly configuration validation."""

    def test_default_fraction(self) -> None:
        """Default fraction is 0.25 (quarter-Kelly)."""
        k = KellyConfig()
        assert k.fraction == 0.25

    def test_zero_fraction_invalid(self) -> None:
        """Fraction must be > 0."""
        with pytest.raises(ValueError, match="fraction"):
            KellyConfig(fraction=0.0)

    def test_negative_fraction_invalid(self) -> None:
        """Negative fraction is invalid."""
        with pytest.raises(ValueError, match="fraction"):
            KellyConfig(fraction=-0.1)

    def test_fraction_above_one_invalid(self) -> None:
        """Fraction > 1 is invalid."""
        with pytest.raises(ValueError, match="fraction"):
            KellyConfig(fraction=1.5)

    def test_fraction_one_valid(self) -> None:
        """Fraction = 1.0 (full Kelly) is valid."""
        k = KellyConfig(fraction=1.0)
        assert k.fraction == 1.0


class TestDataConfig:
    """Tests for data scope configuration."""

    def test_default_leagues(self) -> None:
        """Default includes Top-5 leagues."""
        d = DataConfig()
        assert len(d.leagues) == 5

    def test_valid_season_format(self) -> None:
        """4-digit season codes are valid."""
        d = DataConfig(seasons=["2324", "2425"])
        assert d.seasons == ["2324", "2425"]

    def test_invalid_season_format(self) -> None:
        """Non-4-digit season code raises."""
        with pytest.raises(ValueError, match="4 digits"):
            DataConfig(seasons=["23-24"])

    def test_invalid_season_letters(self) -> None:
        """Non-numeric season code raises."""
        with pytest.raises(ValueError, match="4 digits"):
            DataConfig(seasons=["abcd"])


class TestExperimentConfig:
    """Tests for top-level experiment config."""

    def test_defaults(self) -> None:
        """Default config is valid."""
        c = ExperimentConfig()
        assert c.name == "Unnamed Experiment"
        assert len(c.data.leagues) == 5

    def test_from_yaml(self, tmp_path: Path) -> None:
        """Load config from YAML file."""
        yaml_content = """
name: "Test Experiment"
data:
  leagues: ["ENG-Premier League"]
  seasons: ["2324"]
  markets: ["1x2"]
models:
  - name: lgb
    type: lightgbm
"""
        yaml_path = tmp_path / "test.yaml"
        yaml_path.write_text(yaml_content)
        c = ExperimentConfig.from_yaml(yaml_path)
        assert c.name == "Test Experiment"
        assert len(c.models) == 1
        assert c.data.leagues == ["ENG-Premier League"]

    def test_from_yaml_empty(self, tmp_path: Path) -> None:
        """Empty YAML gives defaults."""
        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("")
        c = ExperimentConfig.from_yaml(yaml_path)
        assert c.name == "Unnamed Experiment"

    def test_from_yaml_missing_file(self) -> None:
        """Missing YAML raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ExperimentConfig.from_yaml(Path("/nonexistent.yaml"))

    def test_calibration_defaults(self) -> None:
        """Default calibration has all three methods."""
        c = CalibrationConfig()
        assert "temperature" in c.methods
        assert "platt" in c.methods
        assert "isotonic" in c.methods

    def test_full_hybrid_config(self, tmp_path: Path) -> None:
        """Full hybrid config from experiments/hybrid_v1.yaml structure."""
        yaml_content = """
name: "Hybrid v1"
models:
  - name: lgb
    type: lightgbm
    params:
      n_estimators: 500
  - name: xgb
    type: xgboost
  - name: hybrid
    type: stacking
    base_models: [lgb, xgb]
    meta_learner: logistic_regression
kelly:
  fraction: 0.25
  shrinkage: true
data:
  seasons: ["2223", "2324"]
  markets: ["1x2", "btts"]
"""
        yaml_path = tmp_path / "hybrid.yaml"
        yaml_path.write_text(yaml_content)
        c = ExperimentConfig.from_yaml(yaml_path)
        assert len(c.models) == 3
        assert c.models[2].type == "stacking"
        assert c.kelly.fraction == 0.25
