import abc
import asyncio
import json
import sys
from asyncio import AbstractEventLoop
from typing import Optional, Union

from aiologger import settings
from aiologger.filters import Filterer
from aiologger.formatters.base import Formatter
from aiologger.formatters.json import JsonFormatter
from aiologger.levels import LogLevel, get_level_name, check_level
from aiologger.records import LogRecord


# Handler relies on any formatter
_default_formatter = Formatter()


class Handler(Filterer):
    """
    Handler instances dispatch logging events to specific destinations.

    The base handler class. Acts as a placeholder which defines the Handler
    interface. Handlers can optionally use Formatter instances to format
    records as desired. By default, no formatter is specified; in this case,
    the 'raw' message as determined by record.message is logged.
    """

    def __init__(
        self,
        level: LogLevel = LogLevel.NOTSET,
        *,
        loop: Optional[AbstractEventLoop] = None,
    ) -> None:
        """
        Initializes the instance - basically setting the formatter to None
        and the filter list to empty.
        """
        Filterer.__init__(self)
        self._level = check_level(level)
        self.formatter: Formatter = _default_formatter
        self._loop: Optional[asyncio.AbstractEventLoop] = loop

    @property
    def loop(self):
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        return self._loop

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value: Union[str, int, LogLevel]):
        """
        Set the logging level of this handler.
        """
        self._level = check_level(value)

    @abc.abstractmethod
    async def emit(self, record: LogRecord) -> None:
        """
        Do whatever it takes to actually log the specified logging record.

        This version is intended to be implemented by subclasses and so
        raises a NotImplementedError.
        """
        raise NotImplementedError(
            "emit must be implemented by Handler subclasses"
        )

    async def handle(self, record: LogRecord) -> bool:
        """
        Conditionally emit the specified logging record.

        Emission depends on filters which may have been added to the handler.
        Returns whether the filter passed the record for emission.
        """
        rv = self.filter(record)
        if rv:
            await self.emit(record)
        return rv

    async def flush(self) -> None:
        """
        Ensure all logging output has been flushed.

        This version does nothing and is intended to be implemented by
        subclasses.
        """
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        """
        Tidy up any resources used by the handler.

        This version removes the handler from an internal map of handlers,
        _handlers, which is used for handler lookup by name. Subclasses
        should ensure that this gets called from overridden close()
        methods.
        """
        raise NotImplementedError(
            "close must be implemented by Handler subclasses"
        )

    async def handle_error(
        self, record: LogRecord, exception: Exception
    ) -> None:
        """
        Handle errors which occur during an emit() call.

        This method should be called from handlers when an exception is
        encountered during an emit() call. This is what is mostly wanted
        for a logging system - most users will not care about errors in
        the logging system, they are more interested in application errors.
        You could, however, replace this with a custom handler if you wish.
        The record which was being processed is passed in to this method.
        """
        if not settings.HANDLE_ERROR_FALLBACK_ENABLED:
            return

        msg = JsonFormatter.format_error_msg(record, exception)
        json.dump(msg, sys.stderr)
        sys.stderr.write("\n")

    def __repr__(self):
        level = get_level_name(self.level)
        return f"<${self.__class__.__name__} (${level})>"
