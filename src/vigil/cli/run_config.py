"""Run-config loading: the CLI defaults that used to live in the interactive menu."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from vigil.cli.defaults import (
    DEFAULT_FIXTURES_PATH,
    DEFAULT_METRICS_INTERVAL,
    DEFAULT_WATCHLIST_PATH,
)
from vigil.detect.data.rules_config import DEFAULT_RULES_CONFIG_PATH
from vigil.ingest.certstream import CERTSTREAM_URL

DEFAULT_RUN_CONFIG_PATH = Path("data/config.yml")


class RunConfig(BaseModel):
    source: str = "certstream"
    certstream_url: str = CERTSTREAM_URL
    fixtures_path: Path = DEFAULT_FIXTURES_PATH
    watchlist: Path = DEFAULT_WATCHLIST_PATH
    rules_config: Path = DEFAULT_RULES_CONFIG_PATH
    output: Path | None = None
    skip_wildcards: bool = True
    detection: bool = False
    metrics: bool = False
    metrics_interval: float = DEFAULT_METRICS_INTERVAL


def load_run_config(path: Path | str = DEFAULT_RUN_CONFIG_PATH) -> RunConfig:
    """Run settings from the config file, or hardcoded defaults if it's missing."""
    path = Path(path)
    if not path.exists():
        return RunConfig()
    return RunConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
