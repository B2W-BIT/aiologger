import unittest
from datetime import datetime
from unittest.mock import ANY
import orjson

from freezegun import freeze_time

from aiologger.formatters.json import JsonFormatter
from aiologger.records import LogRecord
from aiologger.utils import CallableWrapper


class JsonFormatterTests(unittest.TestCase):
    def setUp(self):
        self.record = LogRecord(
            level=30,
            name="aiologger",
            pathname="/aiologger/tests/formatters/test_json_formatter.py",
            lineno=42,
            msg="Xablau",
            exc_info=None,
            func="a_function_name",
            args=None,
        )
        self.formatter = JsonFormatter()

    def test_default_fieldname_is_overwriteable(self):
        formatter = JsonFormatter(default_msg_fieldname="dog")

        self.assertEqual(formatter.default_msg_fieldname, "dog")
        msg = formatter.format(self.record)
        self.assertEqual(msg, formatter.serializer({"dog": "Xablau"}))

    def test_format_adds_exceptions_infos(self):
        self.record.exc_info = "Xena"
        self.record.exc_text = "Xablito"

        self.assertEqual(
            self.formatter.format(self.record),
            self.formatter.serializer(
                {"msg": "Xablau", "exc_info": "Xena", "exc_text": "Xablito"}
            ),
        )

    def test_format_logs_msg_as_is_if_msg_is_a_dict(self):
        self.record.msg = {"dog": "Xablau"}

        msg = self.formatter.format(self.record)
        self.assertEqual(msg, self.formatter.serializer({"dog": "Xablau"}))

    @freeze_time("2019-06-01T19:20:13.401262")
    def test_format_error_msg(self):
        try:
            raise OSError("Broken pipe")
        except Exception as e:
            msg = self.formatter.format_error_msg(
                record=self.record, exception=e
            )
        self.assertEqual(
            msg,
            {
                "record": {
                    "line_number": 42,
                    "level": "WARNING",
                    "file_path": "test_json_formatter.py",
                    "function": "a_function_name",
                    "msg": "Xablau",
                },
                "logged_at": "2019-06-01T19:20:13.401262",
                "logger_exception": {
                    "type": "<class 'OSError'>",
                    "exc": "Broken pipe",
                    "traceback": ANY,
                },
            },
        )

    @freeze_time("2019-06-01T19:20:13.401262")
    def test_format_error_msg_without_traceback(self):
        msg = self.formatter.format_error_msg(
            record=self.record, exception=OSError("Broken pipe")
        )
        self.assertEqual(
            msg,
            {
                "record": {
                    "line_number": 42,
                    "level": "WARNING",
                    "file_path": "test_json_formatter.py",
                    "function": "a_function_name",
                    "msg": "Xablau",
                },
                "logged_at": "2019-06-01T19:20:13.401262",
                "logger_exception": {
                    "type": "<class 'OSError'>",
                    "exc": "Broken pipe",
                    "traceback": ANY,
                },
            },
        )

    def test_json_properly_serialized_when_bytes_object(self):
        self.record.msg = {"dog": "Xablau"}
        custom_formatter = JsonFormatter(serializer=orjson.dumps)
        # Note: json.dumps by default uses this separator (', ', ': ')
        # adding a whitespace whereas with orjson it is not
        # so to have a perfect match is it necessary to specify it
        custom_orjson_serializer_msg = custom_formatter.format(self.record)
        default_json_serializer_msg = self.formatter.serializer(
            {"dog": "Xablau"}, separators=(",", ":")
        )
        self.assertEqual(
            custom_orjson_serializer_msg, default_json_serializer_msg
        )

    def test_raise_exception_when_serialiazed_result_type_not_valid(self):
        with self.assertRaises(TypeError):

            def _serializer(msg, default, **kwargs):
                data = int(5)
                return data

            self.formatter.serializer = _serializer
            returned_msg = self.formatter.format(self.record)


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
            microsecond=666_666,
        )
        result = self.formatter._default_handler(obj)
        # Se o objeto datetime tiver microsecond, `.isoformat()` serializa esse valor
        self.assertEqual(result, "2006-06-06T06:06:06.666666")

    def test_it_converts_exceptions_to_strings(self):
        class MyException(Exception):
            def __repr__(self):
                return "I'm an error"

        obj = MyException("Xablau")
        result = self.formatter._default_handler(obj)
        self.assertEqual(result, "Exception: I'm an error")

    def test_it_calls_callable_objects_and_returns_its_return_value(self):
        obj = CallableWrapper(lambda: "Xablau")
        result = self.formatter._default_handler(obj)
        self.assertEqual(result, "Xablau")

    def test_it_typecasts_object_to_string_if_type_doesnt_match_anything(self):
        obj = 4.2
        result = self.formatter._default_handler(obj)
        self.assertEqual(result, "4.2")

    def test_it_converts_exception_types_to_strings(self):
        class MyException(Exception):
            def __init__(self, errors):
                self.errors = errors

        result = self.formatter._default_handler(MyException)

        self.assertEqual(result, str(MyException))

    def test_it_converts_tracebacks_into_a_list_of_strings(self):
        try:
            raise ValueError("Xablau")
        except Exception as e:
            result = self.formatter._default_handler(e.__traceback__)
            self.assertEqual(len(result), 2)
            self.assertIn('raise ValueError("Xablau")', result[1])
