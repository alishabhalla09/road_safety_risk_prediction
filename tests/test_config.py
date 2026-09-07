from ai.common.config import ConfigLoader


def test_camera_config_loader():
    config = ConfigLoader.get_default_camera_config()
    assert "camera_id" in config
    assert "lanes" in config
    assert "counting_lines" in config
    assert "stop_lines" in config


def test_risk_weights_config_loader():
    config = ConfigLoader.get_risk_weights_config()
    assert "weights" in config
    assert "indicator_normalization_bounds" in config
    assert config["weights"]["red_light"] == 0.20
