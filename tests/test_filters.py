import unittest
from unittest.mock import Mock

from aiologger.filters import StdoutFilter, Filter, Filterer
from aiologger.levels import LogLevel
from tests.utils import make_log_record


class FilterTests(unittest.TestCase):
    def test_filter_allows_records_with_name_equal_to_filter_name(self):
        filter = Filter("A.B.C")
        log_record = make_log_record(name="A.B.C")
        self.assertTrue(filter(log_record))

    def test_filter_allows_any_records_if_filter_name_isnt_provided(self):
        filter = Filter()

        log_record = make_log_record(name="name doesn't matter")
        self.assertTrue(filter(log_record))

        log_record = make_log_record(name="A.B")
        self.assertTrue(filter(log_record))

        log_record = make_log_record(name="A.B.C.D")
        self.assertTrue(filter(log_record))

    def test_filter_allows_records_with_name_starting_with_filter_name(self):
        filter = Filter("A.B")
        log_record = make_log_record(name="A.B.C")
        self.assertTrue(filter(log_record))

    def test_filter_disallows_records_with_name_starting_with_filter_name_that_isnt_a_prefix(
        self
    ):
        filter = Filter("A.B")
        log_record = make_log_record(name="A.BC")
        self.assertFalse(filter(log_record))

    def test_it_disallows_records_with_name_not_starting_with_filter_name(self):
        filter = Filter("A.B")
        log_record = make_log_record(name="B.A")
        self.assertFalse(filter(log_record))

    def test_filters_can_be_subclassed_properly(self):
        """
        Regression test https://github.com/B2W-BIT/aiologger/issues/76
        """

        class MyFilter(Filter):
            filter = Mock(return_value=True)

        filter = MyFilter()
        log_record = make_log_record(name="A.B")

        self.assertTrue(filter(log_record))
        filter.filter.assert_called_once_with(log_record)


class FiltererTests(unittest.TestCase):
    def test_add_filter_adds_filter_only_once(self):
        filter = Filter()
        filterer = Filterer()

        filterer.add_filter(filter)
        self.assertEqual(filterer.filters, [filter])

        filterer.add_filter(filter)
        self.assertEqual(filterer.filters, [filter])

    def test_remove_filter_doesnt_raises_an_error_if_filter_not_in_filters(
        self
    ):
        filter = Filter()
        filterer = Filterer()

        try:
            filterer.remove_filter(filter)
        except Exception as e:
            self.fail(f"Shouldn't raise an error. Error: {e}")

    def test_remove_filter_removes_a_registered_filter(self):
        filter = Filter()
        filterer = Filterer()

        filterer.add_filter(filter)
        filterer.remove_filter(filter)

        self.assertEqual(filterer.filters, [])

    def test_filter_returns_true_if_all_filters_pass(self):
        filterer = Filterer()
        filterer.filters = [
            Mock(return_value=True),
            Mock(return_value=True),
            Mock(return_value=True),
        ]
        record = Mock()

        self.assertTrue(filterer.filter(record))

        for filter in filterer.filters:
            filter.assert_called_with(record)

    def test_filter_returns_false_if_a_filter_fails(self):
        filterer = Filterer()
        filterer.filters = [
            Mock(return_value=True),
            Mock(return_value=False),
            Mock(return_value=True),
        ]
        record = Mock()

        self.assertFalse(filterer.filter(record))

        filterer.filters[0].assert_called_with(record)
        filterer.filters[1].assert_called_with(record)
        filterer.filters[2].assert_not_called()


class StdoutFilterTests(unittest.TestCase):
    def setUp(self):
        self.stdout_filter = StdoutFilter()

    def test_it_filters_records_with_warning_log_level(self):
        record = Mock(levelno=LogLevel.WARNING)
        self.assertFalse(self.stdout_filter.filter(record))

    def test_it_filters_records_with_error_log_level(self):
        record = Mock(levelno=LogLevel.ERROR)
        self.assertFalse(self.stdout_filter.filter(record))

    def test_it_filters_records_with_critical_log_level(self):
        record = Mock(levelno=LogLevel.CRITICAL)
        self.assertFalse(self.stdout_filter.filter(record))

    def test_it_doesnt_filters_records_with_debug_log_level(self):
        record = Mock(levelno=LogLevel.DEBUG)
        self.assertTrue(self.stdout_filter.filter(record))

    def test_it_doesnt_filters_records_with_info_log_level(self):
        record = Mock(levelno=LogLevel.INFO)
        self.assertTrue(self.stdout_filter.filter(record))
