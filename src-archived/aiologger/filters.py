# The following code and documentation was inspired, and in some cases
# copied and modified, from the work of Vinay Sajip and contributors
# on cpython's logging package
from abc import ABC
from typing import List, Callable, Union

from aiologger.levels import LogLevel
from aiologger.records import LogRecord


class Filter:
    """
    Filter instances are used to perform arbitrary filtering of LogRecords.

    Loggers and Handlers can optionally use Filter instances to filter
    records as desired. The base filter class only allows events which are
    below a certain point in the logger hierarchy. For example, a filter
    initialized with "A.B" will allow events logged by loggers "A.B",
    "A.B.C", "A.B.C.D", "A.B.D" etc. but not "A.BB", "B.A.B" etc. If
    initialized with the empty string, all events are passed.
    """

    def __init__(self, name: str = "") -> None:
        """
        Initialize a filter.

        Initialize with the name of the logger which, together with its
        children, will have its events allowed through the filter. If no
        name is specified, allow every event.
        """
        self.name = name
        self.name_length = len(name)

    def filter(self, record: LogRecord) -> bool:
        """
        Determine if the specified record is to be logged.
        """
        if self.name_length == 0:
            return True
        elif self.name == record.name:
            return True
        elif not record.name.startswith(self.name):
            return False
        return record.name[self.name_length] == "."

    def __call__(self, record: LogRecord) -> bool:
        return self.filter(record)


_FilterCallable = Callable[[LogRecord], bool]


class Filterer(ABC):
    """
    A base class for loggers and handlers which allows them to share
    common code.
    """

    def __init__(self):
        """
        Initialize the list of filters to be an empty list.
        """
        self.filters: List[Union[Filter, _FilterCallable]] = []

    def add_filter(self, filter: Filter):
        """
        Add the specified filter to this handler.
        """
        if not (filter in self.filters):
            self.filters.append(filter)

    def remove_filter(self, filter: Filter):
        """
        Remove the specified filter from this handler.
        """
        if filter in self.filters:
            self.filters.remove(filter)

    def filter(self, record: LogRecord) -> bool:
        """
        Determine if a record is loggable by consulting all the filters.

        The default is to allow the record to be logged; any filter can veto
        this and the record is then dropped. Returns a zero value if a record
        is to be dropped, else non-zero.
        """
        for filter in self.filters:
            result = filter(record)
            if not result:
                return False
        return True


class StdoutFilter(Filter):
    _levels = (LogLevel.DEBUG, LogLevel.INFO)

    def filter(self, record: LogRecord) -> bool:
        return record.levelno in self._levels
