import enum
import io
import time
import traceback
from string import Template
from typing import Union, List, Optional
from types import TracebackType

from aiologger.records import LogRecord, ExtendedLogRecord, ExceptionInfo


class FormatStyles(str, enum.Enum):
    PERCENT = "%"
    STRING_TEMPLATE = "$"
    STRING_FORMAT = "{"


class PercentStyle:
    default_format = "%(message)s"
    asctime_format = "%(asctime)s"
    asctime_search = "%(asctime)"

    def __init__(self, fmt: str = None) -> None:
        self._fmt = fmt or self.default_format
        self.uses_time = self._fmt.find(self.asctime_search) >= 0

    def format(self, record: LogRecord) -> str:
        return self._fmt % record.__dict__


class StrFormatStyle(PercentStyle):
    default_format = "{message}"
    asctime_format = "{asctime}"
    asctime_search = "{asctime"

    def format(self, record: LogRecord) -> str:
        return self._fmt.format(**record.__dict__)


class StringTemplateStyle(PercentStyle):
    default_format = "${message}"
    asctime_format = "${asctime}"
    asctime_search = "${asctime}"

    def __init__(self, fmt: str = None) -> None:
        self._fmt = fmt or self.default_format
        self._template = Template(self._fmt)
        self.uses_time = (
            self._fmt.find("$asctime") >= 0
            or self._fmt.find(self.asctime_format) >= 0
        )

    def format(self, record: LogRecord) -> str:
        return self._template.substitute(**record.__dict__)


BASIC_FORMAT = "%(levelname)s:%(name)s:%(message)s"

_STYLES = {
    "%": (PercentStyle, BASIC_FORMAT),
    "{": (StrFormatStyle, "{levelname}:{name}:{message}"),
    "$": (StringTemplateStyle, "${levelname}:${name}:${message}"),
}


class Formatter:
    """
    Formatter instances are used to convert a ExtendedLogRecord to text.

    Formatters need to know how a ExtendedLogRecord is constructed. They are
    responsible for converting a ExtendedLogRecord to (usually) a string which can
    be interpreted by either a human or an external system. The base Formatter
    allows a formatting string to be specified. If none is supplied, the
    default value of "%s(message)" is used.

    The Formatter can be initialized with a format string which makes use of
    knowledge of the ExtendedLogRecord attributes - e.g. the default value mentioned
    above makes use of the fact that the user's message and arguments are pre-
    formatted into a ExtendedLogRecord's message attribute. Currently, the useful
    attributes in a ExtendedLogRecord are described by:

    %(name)s            Name of the logger (logging channel)
    %(levelno)s         Numeric logging level for the message (DEBUG, INFO,
                        WARNING, ERROR, CRITICAL)
    %(levelname)s       Text logging level for the message ("DEBUG", "INFO",
                        "WARNING", "ERROR", "CRITICAL")
    %(pathname)s        Full pathname of the source file where the logging
                        call was issued (if available)
    %(filename)s        Filename portion of pathname
    %(module)s          Module (name portion of filename)
    %(lineno)d          Source line number where the logging call was issued
                        (if available)
    %(funcName)s        Function name
    %(created)f         Time when the ExtendedLogRecord was created (time.time()
                        return value)
    %(asctime)s         Textual time when the ExtendedLogRecord was created
    %(msecs)d           Millisecond portion of the creation time
    %(relativeCreated)d Time in milliseconds when the ExtendedLogRecord was created,
                        relative to the time the logging module was loaded
                        (typically at application startup time)
    %(thread)d          Thread ID (if available)
    %(threadName)s      Thread name (if available)
    %(process)d         Process ID (if available)
    %(message)s         The result of record.get_message(), computed just as
                        the record is emitted
    """

    default_time_format = "%Y-%m-%d %H:%M:%S"
    default_msec_format = "%s,%03d"
    terminator = "\n"

    def __init__(
        self,
        fmt: str = None,
        datefmt: str = None,
        style: Union[str, FormatStyles] = "%",
    ) -> None:
        """
        Initialize the formatter with specified format strings.

        Initialize the formatter either with the specified format string, or a
        default as described above. Allow for specialized date formatting with
        the optional datefmt argument. If datefmt is omitted, you get an
        ISO8601-like (or RFC 3339-like) format.

        Use a style parameter of '%', '{' or '$' to specify that you want to
        use one of %-formatting, :meth:`str.format` (``{}``) formatting or
        :class:`string.Template` formatting in your format string.

        .. versionchanged:: 3.2
           Added the ``style`` parameter.
        """
        if style not in _STYLES:
            valid_styles = ",".join(_STYLES.keys())
            raise ValueError(f"Style must be one of: {valid_styles}")

        self._style = _STYLES[style][0](fmt)
        self._fmt = self._style._fmt
        self.datefmt = datefmt
        self.converter = time.localtime

    def format_time(self, record: LogRecord, datefmt: str = None) -> str:
        """
        Return the creation time of the specified ExtendedLogRecord as formatted text.

        This method should be called from format() by a formatter which
        wants to make use of a formatted time. This method can be overridden
        in formatters to provide for any specific requirement, but the
        basic behaviour is as follows: if datefmt (a string) is specified,
        it is used with time.strftime() to format the creation time of the
        record. Otherwise, an ISO8601-like (or RFC 3339-like) format is used.
        The resulting string is returned. This function uses a user-configurable
        function to convert the creation time to a tuple. By default,
        time.localtime() is used; to change this for a particular formatter
        instance, set the 'converter' attribute to a function with the same
        signature as time.localtime() or time.gmtime(). To change it for all
        formatters, for example if you want all logging times to be shown in GMT,
        set the 'converter' attribute in the Formatter class.
        """
        ct = self.converter(record.created)
        if datefmt:
            return time.strftime(datefmt, ct)
        else:
            t = time.strftime(self.default_time_format, ct)
            return self.default_msec_format % (t, record.msecs)

    def format_exception(self, exception_info: ExceptionInfo) -> str:
        """
        Format and return the specified exception information as a string.

        This default implementation just uses
        traceback.print_exception()
        """
        string_io = io.StringIO()
        tb = exception_info[2]

        traceback.print_exception(
            exception_info[0], exception_info[1], tb, None, string_io
        )

        s = string_io.getvalue()
        string_io.close()
        if s[-1:] == self.terminator:
            s = s[:-1]
        return s

    def format_message(self, record: LogRecord) -> str:
        return self._style.format(record)

    def format_stack(self, stack_info):
        """
        This method is provided as an extension point for specialized
        formatting of stack information.

        The input data is a string as returned from a call to
        :func:`traceback.print_stack`, but with the last trailing newline
        removed.

        The base implementation just returns the value passed in.
        """
        return stack_info

    @staticmethod
    def format_traceback(tb: TracebackType) -> List[str]:
        formatted_tb = "".join(traceback.format_tb(tb))
        return formatted_tb.strip().split("\n")

    def format(self, record: LogRecord) -> str:
        """
        Format the specified record as text.

        The record's attribute dictionary is used as the operand to a
        string formatting operation which yields the returned string.
        Before formatting the dictionary, a couple of preparatory steps
        are carried out. The message attribute of the record is computed
        using LogRecord.get_message(). If the formatting string uses the
        time (as determined by a call to usesTime(), format_time() is
        called to format the event time. If there is exception information,
        it is formatted using format_exception() and appended to the message.
        """
        record.message = record.get_message()
        if self._style.uses_time:
            record.asctime = self.format_time(record, self.datefmt)
        s = self.format_message(record)
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.format_exception(record.exc_info)
        if record.exc_text:
            if s[-1:] != self.terminator:
                s = s + self.terminator
            s = s + record.exc_text
        if record.stack_info:
            if s[-1:] != self.terminator:
                s = s + self.terminator
            s = s + self.format_stack(record.stack_info)
        return s
