"""Tests for config module."""

import os
import json
import tempfile
import pytest


class TestConfig:
    def test_defaults_load(self):
        from utils.config import DEFAULTS, load_config

        # Without a YAML file, should return defaults
        cfg = load_config(path="/nonexistent/config.yaml")
        assert cfg["weights"]["eps"] == DEFAULTS["weights"]["eps"]
        assert cfg["dcf"]["discount_rate"] == DEFAULTS["dcf"]["discount_rate"]

    def test_get_weights_sum_to_one(self):
        from utils.config import get_weights, DEFAULTS

        w = get_weights(DEFAULTS)
        total = sum(w.values())
        assert abs(total - 1.0) < 0.01

    def test_get_weights_normalizes(self):
        from utils.config import get_weights

        cfg = {"weights": {"eps": 1, "roe": 1, "fcf": 1, "balance": 1, "dividend": 1, "dcf": 1, "revenue": 1}}
        w = get_weights(cfg)
        total = sum(w.values())
        assert abs(total - 1.0) < 0.01
        # Each should be ~1/7
        assert abs(w["eps"] - 1 / 7) < 0.01

    def test_get_dcf_params(self):
        from utils.config import get_dcf_params, DEFAULTS

        params = get_dcf_params(DEFAULTS)
        assert "growth_rate_high" in params
        assert "discount_rate" in params
        assert params["discount_rate"] == 0.10

    def test_deep_merge(self):
        from utils.config import _deep_merge

        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"x": 10}, "c": 4}
        result = _deep_merge(base, override)
        assert result["a"]["x"] == 10
        assert result["a"]["y"] == 2
        assert result["b"] == 3
        assert result["c"] == 4

    def test_save_and_load_config(self):
        """Test round-trip save/load (requires pyyaml)."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")

        from utils.config import save_default_config, load_config, DEFAULTS

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            tmppath = f.name

        try:
            save_default_config(tmppath)
            cfg = load_config(tmppath)
            assert cfg["weights"]["eps"] == DEFAULTS["weights"]["eps"]
            assert cfg["dcf"]["growth_rate_high"] == DEFAULTS["dcf"]["growth_rate_high"]
        finally:
            os.unlink(tmppath)
