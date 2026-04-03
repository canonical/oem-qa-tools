"""Unit tests for bmc_manager.utils.config."""

import importlib
import os


def test_config_defaults_when_env_unset(monkeypatch):
    """Config uses defaults when BMC_* env vars are unset."""
    for key in list(os.environ):
        if key.startswith("BMC_"):
            monkeypatch.delenv(key, raising=False)
    # Reload to re-read env
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    c = config_mod.config
    assert c.max_workers == 10
    assert c.timeout == 30
    assert c.log_level == "INFO"
    assert c.enable_cors is False
    assert c.min_retry_delay_seconds == 0.2
    assert c.task_retention_days == 7
    assert c.redfish_request_timeout == 5
    assert c.power_state_poll_interval_seconds == 1.5
    assert c.max_wait_for_state_seconds == 300


def test_config_max_workers_from_env(monkeypatch):
    """Config reads BMC_MAX_WORKERS."""
    monkeypatch.setenv("BMC_MAX_WORKERS", "20")
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.config.max_workers == 20


def test_config_timeout_from_env(monkeypatch):
    """Config reads BMC_TIMEOUT."""
    monkeypatch.setenv("BMC_TIMEOUT", "60")
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.config.timeout == 60


def test_config_min_retry_delay_from_env(monkeypatch):
    """Config reads BMC_MIN_RETRY_DELAY_SECONDS."""
    monkeypatch.setenv("BMC_MIN_RETRY_DELAY_SECONDS", "1.5")
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.config.min_retry_delay_seconds == 1.5


def test_config_enable_cors_true(monkeypatch):
    """Config treats BMC_ENABLE_CORS=true as True."""
    monkeypatch.setenv("BMC_ENABLE_CORS", "true")
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.config.enable_cors is True


def test_config_max_tasks_from_env(monkeypatch):
    """Config reads BMC_MAX_TASKS (0 = no cap)."""
    monkeypatch.setenv("BMC_MAX_TASKS", "10000")
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.config.max_tasks == 10000


def test_config_task_retention_days_from_env(monkeypatch):
    """Config reads BMC_TASK_RETENTION_DAYS."""
    monkeypatch.setenv("BMC_TASK_RETENTION_DAYS", "14")
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.config.task_retention_days == 14


def test_config_redfish_request_timeout_from_env(monkeypatch):
    """Config reads BMC_REDFISH_REQUEST_TIMEOUT."""
    monkeypatch.setenv("BMC_REDFISH_REQUEST_TIMEOUT", "10")
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.config.redfish_request_timeout == 10


def test_config_power_state_poll_interval_from_env(monkeypatch):
    """Config reads BMC_POWER_STATE_POLL_INTERVAL."""
    monkeypatch.setenv("BMC_POWER_STATE_POLL_INTERVAL", "2.0")
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.config.power_state_poll_interval_seconds == 2.0


def test_config_max_wait_for_state_seconds_from_env(monkeypatch):
    """Config reads BMC_MAX_WAIT_FOR_STATE_SECONDS."""
    monkeypatch.setenv("BMC_MAX_WAIT_FOR_STATE_SECONDS", "600")
    import bmc_manager.utils.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.config.max_wait_for_state_seconds == 600
