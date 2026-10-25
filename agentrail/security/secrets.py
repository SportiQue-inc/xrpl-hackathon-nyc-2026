"""Secret lookup: NAME from the environment, or the file named by NAME_FILE (Docker / Kubernetes
secrets, a secret manager's mounted volume). Nothing secret has a default in production."""
from __future__ import annotations

import os


def env() -> str:
    """dev (default on a laptop) or prod. Prod refuses to start without its secrets and turns the
    demo harness (scene runner, simulated devices, dev login) off."""
    return os.environ.get("AGENTRAIL_ENV", "dev").lower()


def is_dev() -> bool:
    return env() != "prod"


def get_secret(name: str, required_in_prod: bool = True) -> str | None:
    v = os.environ.get(name)
    if v:
        return v
    path = os.environ.get(f"{name}_FILE")
    if path and os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    if required_in_prod and not is_dev():
        raise RuntimeError(f"{name} (or {name}_FILE) must be set when AGENTRAIL_ENV=prod")
    return None
