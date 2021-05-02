import unittest
from freezegun import freeze_time

from aiologger.levels import LogLevel
from aiologger.records import LogRecord


class LogRecordTests(unittest.TestCase):
    def test_it_saves_record_creation_time(self):
        with freeze_time("2006-06-06 06:06:06.666666") as t:
            record = LogRecord(
                name="name",
                level=LogLevel.INFO,
                pathname=__file__,
                lineno=666,
                msg="Hello world!",
            )
            self.assertEqual(record.created, 1_149_573_966.666_666)

    def test_get_message_without_args(self):
        record = LogRecord(
            name="name",
            level=LogLevel.INFO,
            pathname=__file__,
            lineno=666,
            msg="Hello world!",
        )
        self.assertEqual(record.get_message(), "Hello world!")

    def test_get_message_with_args(self):
        record = LogRecord(
            name="name",
            level=LogLevel.INFO,
            pathname=__file__,
            lineno=666,
            msg="Dog: %(dog_name)s",
            args=({"dog_name": "Xablau"},),
        )
        self.assertEqual(record.get_message(), "Dog: Xablau")

    def test_it_validates_log_record_args(self):
        with self.assertRaises(ValueError):
            LogRecord(
                name="name",
                level=LogLevel.INFO,
                pathname=__file__,
                lineno=666,
                msg="Dog: %(dog_name)s",
                args=(1, 2, 3),
            )

    def test_str_representation(self):
        record = LogRecord(
            name="name",
            level=LogLevel.INFO,
            pathname=__file__,
            lineno=666,
            msg="Dog: %(dog_name)s",
            args=({"dog_name": "Xablau"},),
        )
        record_str = str(record)

        self.assertIn(record.__class__.__name__, record_str)
        self.assertIn(record.levelname, record_str)
        self.assertIn(record.msg, record_str)
        self.assertIn(record.pathname, record_str)
