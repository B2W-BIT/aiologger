import json
import logging
import traceback
from datetime import datetime
from inspect import istraceback
from typing import Callable, Any


DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
MSG_FIELDNAME = 'msg'


class JsonFormatter(logging.Formatter):
    def __init__(self,
                 serializer: Callable[[Any], str] = json.dumps,
                 default_msg_fieldname: str = None,
                 datetime_format: str = None):
        super(JsonFormatter, self).__init__()
        self.serializer = serializer

        self.default_msg_fieldname = default_msg_fieldname or MSG_FIELDNAME
        self.datetime_format = datetime_format or DATETIME_FORMAT

    def _default_handler(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime(self.datetime_format)
        elif istraceback(obj):
            tb = ''.join(traceback.format_tb(obj))
            return tb.strip().split('\n')
        elif isinstance(obj, Exception):
            return "Exception: %s" % repr(obj)
        elif callable(obj):
            return obj()
        return str(obj)

    def format(self, record: logging.LogRecord) -> str:
        """
        Formats a record and serializes it as a JSON str. If record message isnt
        already a dict, initializes a new dict and uses `default_msg_fieldname`
        as a key as the record msg as the value.
        """
        msg = record.msg
        if not isinstance(record.msg, dict):
            msg = {self.default_msg_fieldname: msg}

        if record.exc_info:
            msg['exc_info'] = record.exc_info
        if record.exc_text:
            msg['exc_text'] = record.exc_text

        return self.serializer(msg, default=self._default_handler)
