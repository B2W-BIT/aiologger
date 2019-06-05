import asyncio
import io
import sys
import traceback
from asyncio import AbstractEventLoop, Task
from typing import Iterable, Optional, Callable, Awaitable, List, NamedTuple

from aiologger.filters import StdoutFilter, Filterer
from aiologger.formatters.base import Formatter
from aiologger.handlers.base import Handler
from aiologger.handlers.streams import AsyncStreamHandler
from aiologger.levels import LogLevel, check_level
from aiologger.records import LogRecord
from aiologger.utils import get_current_frame

_HandlerFactory = Callable[[], Awaitable[Iterable[Handler]]]


class _Caller(NamedTuple):
    filename: str
    line_number: int
    function_name: str
    stack: Optional[str]


def o_o():
    """
    Ordinarily we would use __file__ for this, but frozen modules don't always
    have __file__ set, for some reason (see Issue logging#21736). Thus, we get
    the filename from a handy code object from a function defined in this
    module.
    """
    raise NotImplementedError(
        "I shouldn't be called. My only purpose is to provide "
        "the filename from a handy code object."
    )


# _srcfile is used when walking the stack to check when we've got the first
# caller stack frame, by skipping frames whose filename is that of this
# module's source. It therefore should contain the filename of this module's
# source file.
_srcfile = o_o.__code__.co_filename


class Logger(Filterer):
    def __init__(
        self, *, name="aiologger", level=LogLevel.NOTSET, loop=None
    ) -> None:
        super(Logger, self).__init__()
        self.name = name
        self.level = check_level(level)
        self.parent = None
        self.propagate = True
        self.handlers: List[Handler] = []
        self.disabled = False
        self._loop: Optional[AbstractEventLoop] = loop
        self._was_shutdown = False

        self._dummy_task: Optional[Task] = None

    @property
    def loop(self) -> AbstractEventLoop:
        if self._loop is not None and self._loop.is_running():
            return self._loop
        self._loop = asyncio.get_event_loop()
        return self._loop

    @classmethod
    def with_default_handlers(
        cls,
        *,
        name="aiologger",
        level=LogLevel.NOTSET,
        formatter: Optional[Formatter] = None,
        loop: Optional[AbstractEventLoop] = None,
        **kwargs,
    ):
        self = cls(name=name, level=level, loop=loop, **kwargs)  # type: ignore
        self.add_handler(
            AsyncStreamHandler(
                stream=sys.stdout,
                level=LogLevel.DEBUG,
                formatter=formatter,
                filter=StdoutFilter(),
                loop=loop,
            )
        )
        self.add_handler(
            AsyncStreamHandler(
                stream=sys.stderr,
                level=LogLevel.WARNING,
                formatter=formatter,
                loop=loop,
            )
        )

        return self

    def find_caller(self, stack_info=False) -> _Caller:
        """
        Find the stack frame of the caller so that we can note the source
        file name, line number and function name.
        """
        frame = get_current_frame()
        # On some versions of IronPython, currentframe() returns None if
        # IronPython isn't run with -X:Frames.
        if frame is not None:
            frame = frame.f_back
        while hasattr(frame, "f_code"):
            code = frame.f_code
            filename = code.co_filename
            if filename == _srcfile:
                frame = frame.f_back
                continue
            sinfo = None
            if stack_info:
                sio = io.StringIO()
                sio.write("Stack (most recent call last):\n")
                traceback.print_stack(frame, file=sio)
                sinfo = sio.getvalue()
                if sinfo[-1] == "\n":
                    sinfo = sinfo[:-1]
                sio.close()
            return _Caller(
                filename=code.co_filename or "(unknown file)",
                line_number=frame.f_lineno,
                function_name=code.co_name,
                stack=sinfo,
            )
        return _Caller(
            filename="(unknown file)",
            line_number=0,
            function_name="(unknown function)",
            stack=None,
        )

    async def call_handlers(self, record):
        """
        Pass a record to all relevant handlers.

        Loop through all handlers for this logger and its parents in the
        logger hierarchy. If no handler was found, raises an error. Stop
        searching up the hierarchy whenever a logger with the "propagate"
        attribute set to zero is found - that will be the last logger
        whose handlers are called.
        """
        c = self
        found = 0
        while c:
            for handler in c.handlers:
                found = found + 1
                if record.levelno >= handler.level:
                    await handler.handle(record)
            if not c.propagate:
                c = None  # break out
            else:
                c = c.parent
        if found == 0:
            raise Exception("No handlers could be found for logger")

    def add_handler(self, handler: Handler) -> None:
        """
        Add the specified handler to this logger.
        """
        if not (handler in self.handlers):
            self.handlers.append(handler)

    def remove_handler(self, handler: Handler) -> None:
        """
        Remove the specified handler from this logger.
        """
        if handler in self.handlers:
            self.handlers.remove(handler)

    async def handle(self, record):
        """
        Call the handlers for the specified record.

        This method is used for unpickled records received from a socket, as
        well as those created locally. Logger-level filtering is applied.
        """
        if (not self.disabled) and self.filter(record):
            await self.call_handlers(record)

    async def _log(
        self,
        level,
        msg,
        args,
        exc_info=None,
        extra=None,
        stack_info=False,
        caller: _Caller = None,
    ):

        sinfo = None
        if _srcfile and caller is None:  # type: ignore
            # IronPython doesn't track Python frames, so find_caller raises an
            # exception on some versions of IronPython. We trap it here so that
            # IronPython can use logging.
            try:
                fn, lno, func, sinfo = self.find_caller(stack_info)
            except ValueError:  # pragma: no cover
                fn, lno, func = "(unknown file)", 0, "(unknown function)"
        elif caller:
            fn, lno, func, sinfo = caller
        else:  # pragma: no cover
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
        if exc_info and isinstance(exc_info, BaseException):
            exc_info = (type(exc_info), exc_info, exc_info.__traceback__)

        record = LogRecord(  # type: ignore
            name=self.name,
            level=level,
            pathname=fn,
            lineno=lno,
            msg=msg,
            args=args,
            exc_info=exc_info,
            func=func,
            sinfo=sinfo,
            extra=extra,
        )
        await self.handle(record)

    def __make_dummy_task(self) -> Task:
        async def _dummy(*args, **kwargs):
            return

        return self.loop.create_task(_dummy())

    def is_enabled_for(self, level) -> bool:
        return level >= self.level

    def _make_log_task(self, level, msg, *args, **kwargs) -> Task:
        """
        Creates an asyncio.Task for a msg if logging is enabled for level.
        Returns a dummy task otherwise.
        """
        if not self.is_enabled_for(level):
            if self._dummy_task is None:
                self._dummy_task = self.__make_dummy_task()
            return self._dummy_task

        if kwargs.get("exc_info", False):
            if not isinstance(kwargs["exc_info"], BaseException):
                kwargs["exc_info"] = sys.exc_info()

        coro = self._log(  # type: ignore
            level, msg, *args, caller=self.find_caller(False), **kwargs
        )
        return self.loop.create_task(coro)

    def debug(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'DEBUG'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.debug("Houston, we have a %s", "thorny problem", exc_info=1)
        """
        return self._make_log_task(LogLevel.DEBUG, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'INFO'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.info("Houston, we have an interesting problem", exc_info=1)
        """
        return self._make_log_task(LogLevel.INFO, msg, args, **kwargs)

    def warning(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'WARNING'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.warning("Houston, we have a bit of a problem", exc_info=1)
        """
        return self._make_log_task(LogLevel.WARNING, msg, args, **kwargs)

    warn = warning

    def error(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'ERROR'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.error("Houston, we have a major problem", exc_info=1)
        """
        return self._make_log_task(LogLevel.ERROR, msg, args, **kwargs)

    def critical(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'CRITICAL'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.critical("Houston, we have a major disaster", exc_info=1)
        """
        return self._make_log_task(LogLevel.CRITICAL, msg, args, **kwargs)

    fatal = critical

    def exception(self, msg, *args, exc_info=True, **kwargs) -> Task:
        """
        Convenience method for logging an ERROR with exception information.
        """
        return self.error(msg, *args, exc_info=exc_info, **kwargs)

    async def shutdown(self):
        """
        Perform any cleanup actions in the logging system (e.g. flushing
        buffers).

        Should be called at application exit.
        """
        if self._was_shutdown:
            return
        self._was_shutdown = True
        await self._do_shutdown()

    async def _do_shutdown(self):
        """
        Does actual shutdown
        """
        for handler in reversed(self.handlers):
            if not handler:
                continue
            try:
                if handler.initialized:
                    await handler.flush()
                    await handler.close()

            except Exception:
                """
                Ignore errors which might be caused
                because handlers have been closed but
                references to them are still around at
                application exit. Basically ignore everything, 
                as we're shutting down
                """
                pass
