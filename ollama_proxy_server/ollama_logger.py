"""
Module fro logging in this package
"""

import sys
import os
import logging

# create default config
_FIRST_LOGGER = None


def get_logger(name, default_level="WARNING"):
    """
    used for getting logger in this package
    """
    debug = bool(os.environ.get("DEBUG", False))
    global _FIRST_LOGGER  # pylint: disable=global-statement

    if _FIRST_LOGGER is None:
        if debug:
            print(f"first logger {name}")
        _FIRST_LOGGER = logging.getLogger(name)
        _log = _FIRST_LOGGER
    else:
        _log = _FIRST_LOGGER.getChild(name)
    log_env = f"LOGLEVEL_{name}".replace(".", "__").upper()
    log_level = os.environ.get(log_env, default_level).upper()
    if debug:
        print(f"{log_env}={log_level}", file=sys.stderr)
    try:
        _log.setLevel(log_level)
    except ValueError as e:
        print(f"loglevel {log_level} is not valid, needs to be one of [NOTSET (0), DEBUG (10), INFO (20), WARNING (30), ERROR (40), CRITICAL (50)]", file=sys.stderr)
        print(f"{log_env}={log_level}", file=sys.stderr)
        raise e
    except Exception as e:
        print(f"{log_env}={log_level}", file=sys.stderr)
        raise e
    _log.debug("module loglevel '%s=%s' ", log_env, log_level)
    return _log
