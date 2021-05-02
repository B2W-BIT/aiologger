# The following code and documentation was inspired, and in some cases
# copied and modified, from the work of Vinay Sajip and contributors
# on cpython's logging package
import os
import time
import types
from collections.abc import Mapping
from typing import Optional, Tuple, Type

from aiologger.levels import LogLevel, get_level_name

ExceptionInfo = Tuple[Type[BaseException], BaseException, types.TracebackType]


class LogRecord:
    """
    A LogRecord instance represents an event being logged.

    ExtendedLogRecord instances are created every time something is logged. They
    contain all the information pertinent to the event being logged. The
    main information passed in is in msg and args, which are combined
    using str(msg) % args to create the message field of the record. The
    record also includes information such as when the record was created,
    the source line where the logging call was made, and any exception
    information to be logged.
    """

    def __init__(
        self,
        name: str,
        level: LogLevel,
        pathname: str,
        lineno: int,
        msg,
        args: Optional[Tuple[Mapping]] = None,
        exc_info: Optional[ExceptionInfo] = None,
        func: Optional[str] = None,
        sinfo: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        :param name: The name of the logger used to log the event represented
        by this LogRecord. Note that this name will always have this value,
        even though it may be emitted by a handler attached to a
        different (ancestor) logger.
        :param level: The numeric level of the logging event (one of DEBUG,
        INFO etc.) Note that this is converted to two attributes of the
        LogRecord: levelno for the numeric value and levelname for the
        corresponding level name.
        :param pathname: The full pathname of the source file where the
        logging call was made.
        :param lineno: The line number in the source file where the logging
        call was made.
        :param msg: The event description message, possibly a format string
        with placeholders for variable data.
        :param args: Variable data to merge into the msg argument to obtain
        the event description.
        :param exc_info: An exception tuple with the current exception
        information, or None if no exception information is available.
        :param func: The name of the function or method from which the
        logging call was invoked.
        :param sinfo: A text string representing stack information from the
        base of the stack in the current thread, up to the logging call.
        """
        created_at = time.time()
        self.name = name
        self.msg = msg
        self.args: Optional[Mapping]
        if args:
            if len(args) != 1 or not isinstance(args[0], Mapping):
                raise ValueError(
                    f"Invalid LogRecord args type: {type(args[0])}. "
                    f"Expected Mapping"
                )
            self.args = args[0]
        else:
            self.args = args
        self.levelname = get_level_name(level)
        self.levelno = level
        self.pathname = pathname
        try:
            self.filename = os.path.basename(pathname)
            self.module = os.path.splitext(self.filename)[0]
        except (TypeError, ValueError, AttributeError):
            self.filename = pathname
            self.module = "Unknown module"
        self.exc_info = exc_info
        self.exc_text: Optional[str] = None  # used to cache the traceback text
        self.stack_info = sinfo
        self.lineno = lineno
        self.funcName = func
        self.created = created_at
        self.msecs = (created_at - int(created_at)) * 1000
        self.process = os.getpid()
        self.asctime: Optional[str] = None
        self.message: Optional[str] = None

    def __str__(self):
        return (
            f"<{self.__class__.__name__}: {self.name}, {self.levelname}, "
            f'{self.pathname}, {self.lineno}, "{self.msg}">'
        )

    __repr__ = __str__

    def get_message(self):
        """
        Return the message for this LogRecord after merging any user-supplied
        arguments with the message.
        """
        msg = str(self.msg)
        if self.args:
            msg = msg % self.args
        return msg


class ExtendedLogRecord(LogRecord):
    def __init__(
        self,
        name: str,
        level: LogLevel,
        pathname: str,
        lineno: int,
        msg,
        args: Optional[Tuple[Mapping]],
        exc_info: Optional[ExceptionInfo],
        func: Optional[str] = None,
        sinfo: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            name, level, pathname, lineno, msg, args, exc_info, func, sinfo
        )
        self.extra = kwargs["extra"]
        self.flatten = kwargs["flatten"]
        self.serializer_kwargs = kwargs["serializer_kwargs"]
