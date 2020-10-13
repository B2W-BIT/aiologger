import json
from datetime import timezone
from asyncio import AbstractEventLoop, Task
from typing import Dict, Iterable, Callable, Tuple, Any, Optional, Mapping

from aiologger import Logger
from aiologger.utils import create_task, loop_compat
from aiologger.formatters.base import Formatter
from aiologger.formatters.json import ExtendedJsonFormatter
from aiologger.levels import LogLevel
from aiologger.logger import _Caller
from aiologger.records import ExtendedLogRecord


@loop_compat
class JsonLogger(Logger):
    def __init__(
        self,
        name: str = "aiologger-json",
        level: int = LogLevel.DEBUG,
        flatten: bool = False,
        serializer_kwargs: Dict = None,
        extra: Dict = None,
    ) -> None:
        super().__init__(name=name, level=level)

        self.flatten = flatten

        if serializer_kwargs is None:
            serializer_kwargs = {}
        self.serializer_kwargs = serializer_kwargs

        if extra is None:
            extra = {}
        self.extra = extra

    @classmethod
    def with_default_handlers(  # type: ignore
        cls,
        *,
        name: str = "aiologger-json",
        level: int = LogLevel.NOTSET,
        serializer: Callable[..., str] = json.dumps,
        flatten: bool = False,
        serializer_kwargs: Dict = None,
        extra: Dict = None,
        exclude_fields: Iterable[str] = None,
        tz: timezone = None,
        formatter: Optional[Formatter] = None,
        **kwargs,
    ):
        if formatter is None:
            formatter = ExtendedJsonFormatter(
                serializer=serializer, exclude_fields=exclude_fields, tz=tz
            )
        return super(JsonLogger, cls).with_default_handlers(
            name=name,
            level=level,
            flatten=flatten,
            serializer_kwargs=serializer_kwargs,
            extra=extra,
            formatter=formatter,
            **kwargs,
        )

    def _log(  # type: ignore
        self,
        level: LogLevel,
        msg: Any,
        args: Optional[Tuple[Mapping]],
        exc_info=None,
        extra: Dict = None,
        stack_info=False,
        flatten: bool = False,
        serializer_kwargs: Dict = None,
        caller: _Caller = None,
    ) -> Task:
        """
        Low-level logging routine which creates a ExtendedLogRecord and
        then calls all the handlers of this logger to handle the record.

        Overwritten to properly handle log methods kwargs
        """
        sinfo = None
        if caller:
            fn, lno, func, sinfo = caller
        else:  # pragma: no cover
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
        if exc_info and isinstance(exc_info, BaseException):
            exc_info = (type(exc_info), exc_info, exc_info.__traceback__)

        joined_extra = {}
        joined_extra.update(self.extra)

        if extra:
            joined_extra.update(extra)

        record = ExtendedLogRecord(
            name=self.name,
            level=level,
            pathname=fn,
            lineno=lno,
            msg=msg,
            args=args,
            exc_info=exc_info,
            func=func,
            sinfo=sinfo,
            extra=joined_extra,
            flatten=flatten or self.flatten,
            serializer_kwargs=serializer_kwargs or self.serializer_kwargs,
        )
        return create_task(self.handle(record))
