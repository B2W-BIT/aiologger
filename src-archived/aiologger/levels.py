import enum
from typing import Union


class LogLevel(enum.IntEnum):
    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10
    NOTSET = 0


NAME_TO_LEVEL = {level: LogLevel[level].value for level in LogLevel.__members__}
LEVEL_TO_NAME = {level.value: level.name for level in LogLevel}


def get_level_name(level: Union[int, LogLevel]) -> str:
    """
    Return the textual representation of logging level 'level'.

    If the level is one of the predefined levels (CRITICAL, ERROR, WARNING,
    INFO, DEBUG) then you get the corresponding string.

    If a numeric value corresponding to one of the defined levels is passed
    in, the corresponding string representation is returned.
    """
    try:
        return LEVEL_TO_NAME[level]
    except KeyError as e:
        raise ValueError(f"Unkown level name: {level}") from e


def check_level(level: Union[str, int, LogLevel]) -> int:
    if isinstance(level, int):
        if level not in LEVEL_TO_NAME:
            raise ValueError(f"Unknown level: {level}")
        return level
    elif isinstance(level, str):
        try:
            return NAME_TO_LEVEL[level]
        except KeyError:
            raise ValueError(f"Unknown level: {level}")
    else:
        raise TypeError(f"Level not an Union[str, int, LogLevel]: {level}")
