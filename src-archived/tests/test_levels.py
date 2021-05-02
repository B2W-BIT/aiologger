import unittest

from aiologger.levels import check_level, get_level_name, LogLevel


class CheckLevelTests(unittest.TestCase):
    def test_it_raises_a_ValueError_if_level_is_unknown(self):
        for unknown_level in ["PERIGO", "XABLAU", 42]:
            with self.assertRaises(ValueError):
                check_level(unknown_level)

    def test_it_raises_a_TypeError_if_level_has_an_invalid_type(self):
        for invalid_level in [None, {}, [], b"warn"]:
            with self.assertRaises(TypeError):
                check_level(invalid_level)

    def test_it_converts_str_level_into_an_integer(self):
        self.assertEqual(check_level("CRITICAL"), 50)
        self.assertEqual(check_level("FATAL"), 50)
        self.assertEqual(check_level("ERROR"), 40)
        self.assertEqual(check_level("WARNING"), 30)
        self.assertEqual(check_level("WARN"), 30)
        self.assertEqual(check_level("INFO"), 20)
        self.assertEqual(check_level("DEBUG"), 10)
        self.assertEqual(check_level("NOTSET"), 0)

    def test_it_returns_level_as_is_if_level_is_a_valid_integer_level(self):
        self.assertEqual(check_level(50), 50)


class GetLevelNameTests(unittest.TestCase):
    def test_it_raises_an_error_if_level_is_invalid(self):
        with self.assertRaises(ValueError):
            get_level_name(666)

    def test_it_returns_the_proper_textual_representation_of_the_name(self):
        self.assertEqual(get_level_name(20), "INFO")
        self.assertEqual(get_level_name(LogLevel.INFO), "INFO")
