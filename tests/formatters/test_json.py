import unittest
from datetime import datetime
from logging import LogRecord

from aiologger.formatters.json import JsonFormatter


class JsonFormatterTests(unittest.TestCase):
    def setUp(self):
        self.record = LogRecord(
            level=30,
            name='aiologger',
            pathname="/aiologger/tests/formatters/test_json.py",
            lineno=42,
            msg="Xablau",
            exc_info=None,
            args=None
        )
        self.formatter = JsonFormatter()

    def test_default_fieldname_is_overwriteable(self):
        formatter = JsonFormatter(default_msg_fieldname='dog')

        self.assertEqual(formatter.default_msg_fieldname, 'dog')
        msg = formatter.format(self.record)
        self.assertEqual(msg, formatter.serializer({'dog': 'Xablau'}))

    def test_format_adds_exceptions_infos(self):
        self.record.exc_info = "Xena"
        self.record.exc_text = 'Xablito'

        self.assertEqual(
            self.formatter.format(self.record),
            self.formatter.serializer({
                'msg': 'Xablau',
                'exc_info': 'Xena',
                'exc_text': 'Xablito'
            })
        )

    def test_format_logs_msg_as_is_if_msg_is_a_dict(self):
        self.record.msg = {'dog': 'Xablau'}

        msg = self.formatter.format(self.record)
        self.assertEqual(
            msg,
            self.formatter.serializer({
                'dog': 'Xablau'
            })
        )


class DefaultHandlerTests(unittest.TestCase):
    def setUp(self):
        self.formatter = JsonFormatter()

    def test_it_converts_datetime_objects_to_strings(self):
        obj = datetime(
            year=2006,
            month=6,
            day=6,
            hour=6,
            minute=6,
            second=6,
            microsecond=666666
        )
        result = self.formatter._default_handler(obj)
        self.assertEqual(result, '2006-06-06T06:06:06.666666')

    def test_it_converts_exceptions_to_strings(self):
        obj = KeyError("Xablau")
        result = self.formatter._default_handler(obj)
        self.assertEqual(result, "Exception: KeyError('Xablau',)")

    def test_it_calls_callable_objects_and_returns_its_return_value(self):
        obj = lambda: "Xablau"
        result = self.formatter._default_handler(obj)
        self.assertEqual(result, "Xablau")

    def test_it_typecasts_object_to_string_if_type_doesnt_match_anything(self):
        obj = 4.2
        result = self.formatter._default_handler(obj)
        self.assertEqual(result, "4.2")

