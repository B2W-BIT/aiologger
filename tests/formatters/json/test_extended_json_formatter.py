import json
import orjson
import unittest
from datetime import timezone, timedelta
from unittest.mock import patch, ANY

from freezegun import freeze_time

from aiologger.formatters.json import (
    ExtendedJsonFormatter,
    LOG_LEVEL_FIELDNAME,
    LINE_NUMBER_FIELDNAME,
)
from aiologger.records import ExtendedLogRecord


class ExtendedJsonFormatterTests(unittest.TestCase):
    def setUp(self):
        self.formatter = ExtendedJsonFormatter()
        self.record = ExtendedLogRecord(
            level=30,
            name="aiologger",
            pathname="/aiologger/tests/formatters/test_json_formatter.py",
            func="xablaufunc",
            lineno=42,
            msg={"dog": "Xablau", "action": "bark"},
            exc_info=None,
            args=None,
            extra=None,
            flatten=False,
            serializer_kwargs={},
        )

    def test_it_uses_default_log_fields_if_none_are_excluded_on_initialization(
        self
    ):
        formatter = ExtendedJsonFormatter()
        self.assertEqual(
            ExtendedJsonFormatter.default_fields, formatter.log_fields
        )

    def test_default_log_fields_can_be_excluded_with_exclude_fields_initialization_argument(
        self
    ):
        formatter = ExtendedJsonFormatter(exclude_fields=(LOG_LEVEL_FIELDNAME,))
        self.assertNotIn(LOG_LEVEL_FIELDNAME, formatter.log_fields)

    def test_formatter_fields_for_record_with_default_fields(self):
        result = dict(self.formatter.formatter_fields_for_record(self.record))
        self.assertEqual(
            result,
            {
                "logged_at": ANY,
                "line_number": 42,
                "function": "xablaufunc",
                "level": "WARNING",
                "file_path": "/aiologger/tests/formatters/test_json_formatter.py",
            },
        )

    @freeze_time("2018-06-16T10:16:00-03:00")
    def test_formatter_with_tz_info_utc(self):
        """
        Check that, if tz is not None, log messages must have timezone info
        """
        formatter = ExtendedJsonFormatter(tz=timezone.utc)
        result = dict(formatter.formatter_fields_for_record(self.record))
        self.assertEqual(
            result,
            {
                "logged_at": "2018-06-16T13:16:00+00:00",
                "line_number": 42,
                "function": "xablaufunc",
                "level": "WARNING",
                "file_path": "/aiologger/tests/formatters/test_json_formatter.py",
            },
        )

    @freeze_time("2018-06-16T16:20:00+00:00")
    def test_formatter_with_tz_info_america_sao_paulo_from_utc(self):
        """
        Current time is UTC and we want logs to be generated on America/Sao_Paulo (-3)
        """
        tz_america = timezone(timedelta(hours=-3))
        formatter = ExtendedJsonFormatter(tz=tz_america)
        result = dict(formatter.formatter_fields_for_record(self.record))
        self.assertEqual(
            result,
            {
                "logged_at": "2018-06-16T13:20:00-03:00",
                "line_number": 42,
                "function": "xablaufunc",
                "level": "WARNING",
                "file_path": "/aiologger/tests/formatters/test_json_formatter.py",
            },
        )

    @freeze_time("2018-06-16T15:20:00-07:00")
    def test_formatter_with_tz_info_other_zone(self):
        """
        Current time is NOT UTC (is -7) and we want logs to be generate in America/Sao_Paulo (-3)
        """
        tz_america = timezone(timedelta(hours=-3))
        formatter = ExtendedJsonFormatter(tz=tz_america)
        result = dict(formatter.formatter_fields_for_record(self.record))
        self.assertEqual(
            result,
            {
                "logged_at": "2018-06-16T19:20:00-03:00",
                "line_number": 42,
                "function": "xablaufunc",
                "level": "WARNING",
                "file_path": "/aiologger/tests/formatters/test_json_formatter.py",
            },
        )

    def test_formatter_fields_for_record_with_excluded_fields(self):
        log_fields = {LOG_LEVEL_FIELDNAME, LINE_NUMBER_FIELDNAME}

        with patch.object(self.formatter, "log_fields", log_fields):
            result = dict(
                self.formatter.formatter_fields_for_record(self.record)
            )
            self.assertEqual(result, {"line_number": 42, "level": "WARNING"})

    def test_default_format(self):
        serialized_result = self.formatter.format(self.record)
        content = json.loads(serialized_result)
        self.assertEqual(
            content,
            {
                "logged_at": ANY,
                "line_number": 42,
                "function": "xablaufunc",
                "level": "WARNING",
                "file_path": "/aiologger/tests/formatters/test_json_formatter.py",
                "msg": {"dog": "Xablau", "action": "bark"},
            },
        )

    def test_flatten_record_attr_adds_msg_to_root(self):
        self.record.flatten = True
        serialized_result = self.formatter.format(self.record)

        content = json.loads(serialized_result)
        self.assertEqual(
            content,
            {
                "logged_at": ANY,
                "line_number": 42,
                "function": "xablaufunc",
                "level": "WARNING",
                "file_path": "/aiologger/tests/formatters/test_json_formatter.py",
                "dog": "Xablau",
                "action": "bark",
            },
        )

    def test_flatten_record_attr_does_nothing_if_msg_isnt_a_dict_instance(self):
        self.record.flatten = True
        self.record.msg = "Xablau, the dog"
        serialized_result = self.formatter.format(self.record)

        content = json.loads(serialized_result)
        self.assertEqual(
            content,
            {
                "logged_at": ANY,
                "line_number": 42,
                "function": "xablaufunc",
                "level": "WARNING",
                "file_path": "/aiologger/tests/formatters/test_json_formatter.py",
                "msg": "Xablau, the dog",
            },
        )

    def test_serialized_kwargs_record_attr_is_passed_to_instance_serialized_function(
        self
    ):
        def _serializer(msg, default, **kwargs):
            data = json.dumps({**msg, **kwargs})
            return data

        self.record.serializer_kwargs = {"indent": 2, "sort_keys": True}
        expected_msg = {
            "logged_at": ANY,
            "line_number": 42,
            "function": "xablaufunc",
            "level": "WARNING",
            "file_path": "/aiologger/tests/formatters/test_json_formatter.py",
            "msg": {"dog": "Xablau", "action": "bark"},
        }
        self.formatter.serializer = _serializer
        returned_msg = self.formatter.format(self.record)

        self.assertEqual(
            {**expected_msg, **self.record.serializer_kwargs},
            json.loads(returned_msg),
        )

    def test_extra_record_attr_adds_content_to_root_of_msg(self):
        self.record.extra = {"female_dog": "Xena"}
        serialized_result = self.formatter.format(self.record)

        content = json.loads(serialized_result)
        self.assertEqual(
            content,
            {
                "logged_at": ANY,
                "line_number": 42,
                "function": "xablaufunc",
                "level": "WARNING",
                "file_path": "/aiologger/tests/formatters/test_json_formatter.py",
                "msg": {"dog": "Xablau", "action": "bark"},
                "female_dog": "Xena",
            },
        )

    @freeze_time("2018-06-16T10:16:00-03:00")
    def test_json_properly_serialized_when_bytes_object(self):
        # orjson
        custom_formatter = ExtendedJsonFormatter(serializer=orjson.dumps)
        # Note: json.dumps by default uses this separator (', ', ': ')
        # adding a whitespace whereas with orjson it is not
        # so to have a perfect match is it necessary to specify it
        custom_orjson_serializer_msg = custom_formatter.format(self.record)

        # json
        serialized_result = self.formatter.format(self.record)
        content = json.loads(serialized_result)
        default_json_serializer_msg = self.formatter.serializer(
            content, separators=(",", ":")
        )

        self.assertEqual(
            custom_orjson_serializer_msg, default_json_serializer_msg
        )
