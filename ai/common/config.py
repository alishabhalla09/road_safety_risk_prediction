import json
import os
from typing import Any

import yaml


class ConfigLoader:
    """Utility class to load and validate camera scene, YOLO, and risk configurations."""

    @staticmethod
    def load_json(filepath: str) -> dict[str, Any]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_yaml(filepath: str) -> dict[str, Any]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        with open(filepath, encoding="utf-8") as f:
            return yaml.safe_load(f)

    @classmethod
    def get_default_camera_config(cls, base_dir: str | None = None) -> dict[str, Any]:
        dir_path = base_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../configs"))
        config_path = os.path.join(dir_path, "default_camera_config.json")
        return cls.load_json(config_path)

    @classmethod
    def get_risk_weights_config(cls, base_dir: str | None = None) -> dict[str, Any]:
        dir_path = base_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../configs"))
        config_path = os.path.join(dir_path, "risk_weights.json")
        return cls.load_json(config_path)
