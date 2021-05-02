from os import getenv
from typing import Optional


def get_bool_env(name: str, default: Optional[bool] = None) -> bool:
    value = getenv(name, default)
    if not value:
        return False
    if value in ("False", "false", "0"):
        return False
    return True


HANDLE_ERROR_FALLBACK_ENABLED = get_bool_env(
    "AIOLOGGER_HANDLE_ERROR_FALLBACK_ENABLED", default=True
)
