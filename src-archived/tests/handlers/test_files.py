import asyncio
import datetime
import os
import time
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import asynctest
from aiofiles.threadpool import AsyncTextIOWrapper
from asynctest import CoroutineMock, Mock
from freezegun import freeze_time

from aiologger.formatters.base import Formatter
from aiologger.handlers.files import (
    AsyncFileHandler,
    BaseAsyncRotatingFileHandler,
    AsyncTimedRotatingFileHandler,
    RolloverInterval,
    ONE_WEEK_IN_SECONDS,
    ONE_DAY_IN_SECONDS,
    ONE_MINUTE_IN_SECONDS,
    ONE_HOUR_IN_SECONDS,
)
from aiologger.records import LogRecord
from tests.utils import make_log_record


class AsyncFileHandlerTests(asynctest.TestCase):
    async def setUp(self):
        self.record = LogRecord(
            name="aiologger",
            level=20,
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None,
        )
        self.temp_file = NamedTemporaryFile()

    async def tearDown(self):
        patch.stopall()
        self.temp_file.close()

    async def test_initialization(self):
        mode = "x"
        encoding = "utf-8"
        loop = Mock()
        handler = AsyncFileHandler(
            filename=self.temp_file.name,
            mode=mode,
            encoding=encoding,
            loop=loop,
        )

        self.assertIsInstance(handler, AsyncFileHandler)

        self.assertEqual(handler.absolute_file_path, self.temp_file.name)
        self.assertEqual(handler.mode, mode)
        self.assertEqual(handler.encoding, encoding)
        self.assertEqual(handler.loop, loop)

        self.assertIsNone(handler.stream)

    async def test_init_gets_the_running_event_loop(self):
        handler = AsyncFileHandler(filename=self.temp_file.name)

        self.assertIsInstance(handler.loop, asyncio.AbstractEventLoop)

    async def test_close_closes_the_file(self):
        handler = AsyncFileHandler(filename=self.temp_file.name)

        await handler._init_writer()
        self.assertFalse(handler.stream is None)
        self.assertIsInstance(handler.stream, AsyncTextIOWrapper)
        self.assertFalse(handler.stream.closed)

        await handler.close()
        self.assertTrue(handler.stream is None)

    async def test_emit_writes_log_records_into_the_file(self):
        handler = AsyncFileHandler(filename=self.temp_file.name)

        await handler.emit(self.record)
        await handler.emit(self.record)

        await handler.flush()

        with open(self.temp_file.name) as fp:
            content = fp.read()

        self.assertEqual(content, "Xablau!\nXablau!\n")

        await handler.close()

    async def test_init_stream_initializes_a_nonblocking_file_writer(self):
        handler = AsyncFileHandler(filename=self.temp_file.name)

        await handler._init_writer()

        self.assertIsInstance(handler.stream, AsyncTextIOWrapper)
        self.assertFalse(handler.stream.closed)
        self.assertEqual(handler.stream._file.name, self.temp_file.name)

        await handler.close()

    async def test_writer_is_initialized_only_once(self):
        handler = AsyncFileHandler(filename=self.temp_file.name)

        with patch(
            "aiologger.handlers.files.aiofiles.open",
            CoroutineMock(
                return_value=Mock(write=CoroutineMock(), flush=CoroutineMock())
            ),
        ) as open:
            await asyncio.gather(
                *(handler.emit(self.record) for _ in range(42))
            )
            open.assert_awaited_once()


class BaseAsyncRotatingFileHandlerTests(asynctest.TestCase):
    async def setUp(self):
        self.temp_file = NamedTemporaryFile(delete=False)

    async def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    async def test_rotate_renames_the_source_file_if_a_rotator_isnt_available(
        self
    ):
        handler = BaseAsyncRotatingFileHandler(filename=self.temp_file.name)
        destination = self.temp_file.name + "1"

        self.assertTrue(os.path.exists(self.temp_file.name))
        self.assertFalse(os.path.exists(destination))

        await handler.rotate(self.temp_file.name, destination)

        self.assertFalse(os.path.exists(self.temp_file.name))
        self.assertTrue(os.path.exists(destination))

    async def test_rotate_calls_the_rotator_if_one_is_avaialble(self):
        handler = BaseAsyncRotatingFileHandler(filename=self.temp_file.name)
        handler.rotator = Mock()
        destination = self.temp_file.name + "1"

        await handler.rotate(self.temp_file.name, destination)

        handler.rotator.assert_called_once_with(
            self.temp_file.name, destination
        )

    async def test_emit_does_rollover_if_should_rollover(self):
        handler = BaseAsyncRotatingFileHandler(filename=self.temp_file.name)
        handler.should_rollover = Mock(return_value=True)

        async def rollover_is_done():
            """
            sleep is needed so that the loop can schedule the other
            `do_rollover` coroutines, simulating a real `do_rollover` behaviour
            """
            await asyncio.sleep(0.1)
            handler.should_rollover.return_value = False

        handler.do_rollover = CoroutineMock(side_effect=rollover_is_done)

        await asyncio.gather(
            *(
                handler.emit(
                    LogRecord(
                        name=str(i),
                        level=20,
                        pathname="/aiologger/tests/test_logger.py",
                        lineno=17,
                        msg="Xablau!",
                        exc_info=None,
                        args=None,
                    )
                )
                for i in range(42)
            )
        )

        handler.do_rollover.assert_awaited_once()

    async def test_emit_awaits_for_handle_error_is_an_exceptions_is_raised(
        self
    ):
        handler = BaseAsyncRotatingFileHandler(filename=self.temp_file.name)
        handler.should_rollover = Mock(return_value=False)
        exc = OSError()
        with patch(
            "aiologger.handlers.files.AsyncFileHandler.emit", side_effect=exc
        ), patch.object(
            handler, "handle_error", CoroutineMock()
        ) as handleError:
            log_record = LogRecord(
                name="Xablau",
                level=20,
                pathname="/aiologger/tests/test_logger.py",
                lineno=17,
                msg="Xablau!",
                exc_info=None,
                args=None,
            )
            await handler.emit(log_record)
            handleError.assert_awaited_once_with(log_record, exc)

    async def test_rotation_filename_uses_the_default_if_a_namer_isnt_provided(
        self
    ):
        handler = BaseAsyncRotatingFileHandler(filename=self.temp_file.name)
        self.assertEqual(handler.rotation_filename("Xablau"), "Xablau")

    async def test_rotation_filename_delegates_to_the_namer_if_a_namer_is_provided(
        self
    ):
        namer = Mock(return_value="Xena")
        handler = BaseAsyncRotatingFileHandler(
            filename=self.temp_file.name, namer=namer
        )

        self.assertEqual(handler.rotation_filename("Xablau"), "Xena")
        namer.assert_called_once_with("Xablau")


class AsyncTimedRotatingFileHandlerTests(asynctest.TestCase):
    async def setUp(self):
        self.log_record = LogRecord(
            name="aiologger",
            level=20,
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None,
        )
        self.temp_file = NamedTemporaryFile(delete=False)
        self.files_to_remove = [self.temp_file.name]

    async def tearDown(self):
        patch.stopall()
        for file_path in self.files_to_remove:
            if os.path.exists(file_path):
                os.unlink(file_path)

    @freeze_time()
    async def test_initialization_with_minutes_rollover_interval(self):
        handler = AsyncTimedRotatingFileHandler(
            filename="/a/random/filepath",
            when=RolloverInterval.MINUTES,
            backup_count=1,
        )
        self.assertEqual(handler.interval, ONE_MINUTE_IN_SECONDS)
        self.assertEqual(
            handler.rollover_at, int(time.time()) + ONE_MINUTE_IN_SECONDS
        )
        await handler.close()

    @freeze_time()
    async def test_initialization_with_hours_rollover_interval(self):
        handler = AsyncTimedRotatingFileHandler(
            filename="/a/random/filepath",
            when=RolloverInterval.HOURS,
            backup_count=1,
        )
        self.assertEqual(handler.interval, ONE_HOUR_IN_SECONDS)
        self.assertEqual(
            handler.rollover_at, int(time.time()) + ONE_HOUR_IN_SECONDS
        )
        await handler.close()

    async def test_rollover(self):
        handler = AsyncTimedRotatingFileHandler(
            filename=self.temp_file.name,
            when=RolloverInterval.SECONDS,
            backup_count=1,
        )
        formatter = Formatter("%(asctime)s %(message)s")
        handler.formatter = formatter
        r1 = make_log_record(msg="testing - initial")
        await handler.emit(r1)
        self.assertTrue(os.path.exists(self.temp_file.name))

        await asyncio.sleep(1.1)

        r2 = make_log_record(msg="testing - after delay")
        await handler.emit(r2)
        await handler.close()
        # At this point, we should have a recent rotated file which we
        # can test for the existence of. However, in practice, on some
        # machines which run really slowly, we don't know how far back
        # in time to go to look for the log file. So, we go back a fair
        # bit, and stop as soon as we see a rotated file. In theory this
        # could of course still fail, but the chances are lower.
        found = False
        now = datetime.datetime.now()
        GO_BACK = 5 * 60  # seconds
        for secs in range(GO_BACK):
            prev = now - datetime.timedelta(seconds=secs)
            fn = self.temp_file.name + prev.strftime(".%Y-%m-%d_%H-%M-%S")
            found = os.path.exists(fn)
            if found:
                self.files_to_remove.append(fn)
                break

        self.assertTrue(
            found, msg=f"No rotated files found, went back {GO_BACK} seconds"
        )

    async def test_rollover_delete_old_files(self):
        with freeze_time() as frozen_datetime:
            handler = AsyncTimedRotatingFileHandler(
                filename=self.temp_file.name,
                when=RolloverInterval.SECONDS,
                backup_count=1,
            )
            with patch.object(handler, "_delete_files", CoroutineMock()):
                for _ in range(3):
                    await handler.emit(self.log_record)
                    frozen_datetime.tick()
                handler._delete_files.assert_awaited_once()

            await handler.close()

    async def test_delete_files(self):
        handler = AsyncTimedRotatingFileHandler(
            filename=self.temp_file.name,
            when=RolloverInterval.SECONDS,
            backup_count=1,
        )

        file_paths = [NamedTemporaryFile(delete=False).name for _ in range(3)]
        await handler._init_writer()
        await handler._delete_files(file_paths)

        for file_path in file_paths:
            self.assertFalse(os.path.exists(file_path))

        await handler.close()

    async def test_files_to_delete_returns_an_empty_list_if_there_is_nothing_to_delete(
        self
    ):
        handler = AsyncTimedRotatingFileHandler(
            filename=self.temp_file.name,
            when=RolloverInterval.SECONDS,
            backup_count=1,
        )
        self.assertEqual(await handler.get_files_to_delete(), [])

    async def test_rollover_deletes_the_next_destination_file_path_if_it_already_exists(
        self
    ):
        with freeze_time("2019-01-20 20:22:49") as frozen_datetime:
            with patch(
                "aiologger.handlers.files.os.stat",
                return_value=Mock(
                    st_mtime=frozen_datetime.time_to_freeze.timestamp()
                    - time.altzone
                ),
            ), patch("aiologger.handlers.files.os.unlink") as unlink:
                new_file_path = f"{self.temp_file.name}.2019-01-20_20-22-49"
                os.open(new_file_path, os.O_CREAT)

                self.assertTrue(os.path.exists(new_file_path))
                handler = AsyncTimedRotatingFileHandler(
                    filename=self.temp_file.name,
                    when=RolloverInterval.SECONDS,
                    backup_count=1,
                    utc=True,
                )
                frozen_datetime.tick()
                await handler.emit(self.log_record)

                unlink.assert_called_once_with(new_file_path)

        await handler.close()

    async def test_rollover_happens_before_a_logline_is_emitted(self):
        handler = AsyncTimedRotatingFileHandler(
            filename=self.temp_file.name,
            when=RolloverInterval.SECONDS,
            backup_count=1,
        )
        formatter = Formatter("%(asctime)s %(message)s")
        handler.formatter = formatter

        self.assertTrue(os.path.exists(self.temp_file.name))

        await asyncio.sleep(1.1)

        record = make_log_record(msg="testing - initial")
        await handler.emit(record)
        await handler.close()

    async def test_invalid_rotation_interval(self):
        for invalid_interval in ("X", "W", "W7", "Xablau"):
            with self.assertRaises(ValueError):
                AsyncTimedRotatingFileHandler(
                    filename=self.temp_file.name, when=invalid_interval
                )

    async def test_compute_rollover_daily_attime(self):
        current_time = 0
        at_time = datetime.time(12, 0, 0)
        handler = AsyncTimedRotatingFileHandler(
            self.temp_file.name,
            when=RolloverInterval.MIDNIGHT,
            interval=1,
            backup_count=0,
            utc=True,
            at_time=at_time,
        )
        try:
            actual = handler.compute_rollover(current_time)
            self.assertEqual(actual, current_time + 12 * 60 * 60)

            actual = handler.compute_rollover(current_time + 13 * 60 * 60)
            self.assertEqual(actual, current_time + 36 * 60 * 60)
        finally:
            await handler.close()

    async def test_compute_rollover_daily(self):
        current_time = 0
        handler = AsyncTimedRotatingFileHandler(
            self.temp_file.name,
            when=RolloverInterval.MIDNIGHT,
            interval=1,
            backup_count=0,
            utc=True,
        )
        try:
            actual = handler.compute_rollover(current_time)
            self.assertEqual(actual, current_time + ONE_DAY_IN_SECONDS)
        finally:
            await handler.close()

    async def test_compute_rollover_weekly_attime(self):
        current_time = int(time.time())
        today = current_time - current_time % 86400

        at_time = datetime.time(12, 0, 0)

        week_day = time.gmtime(today).tm_wday
        for day, interval in enumerate(RolloverInterval.WEEK_DAYS):
            handler = AsyncTimedRotatingFileHandler(
                filename=self.temp_file.name,
                when=interval,
                interval=1,
                backup_count=0,
                utc=True,
                at_time=at_time,
            )
            try:
                if week_day > day:
                    # The rollover day has already passed this week, so we
                    # go over into next week
                    expected = 7 - week_day + day
                else:
                    expected = day - week_day
                # At this point expected is in days from now, convert to seconds
                expected *= ONE_DAY_IN_SECONDS
                # Add in the rollover time
                expected += 12 * 60 * 60
                # Add in adjustment for today
                expected += today
                actual = handler.compute_rollover(today)
                self.assertEqual(
                    actual, expected, msg=f"failed in timezone: {time.timezone}"
                )

                if day == week_day:
                    # goes into following week
                    expected += ONE_WEEK_IN_SECONDS

                actual = handler.compute_rollover(today + 13 * 60 * 60)
                self.assertEqual(
                    actual, expected, msg=f"failed in timezone: {time.timezone}"
                )
            finally:
                await handler.close()

    async def test_it_calls_handler_error_if_emit_fails(self):
        temp_file = NamedTemporaryFile(delete=False)
        handler = AsyncFileHandler(temp_file.name)
        log_record = LogRecord(
            name="Xablau",
            level=20,
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None,
        )
        await handler._init_writer()
        exc = Exception("Xablau")
        with patch.object(
            handler.stream, "write", side_effect=exc
        ), patch.object(
            handler, "handle_error", CoroutineMock()
        ) as handle_error:
            await handler.emit(log_record)
            handle_error.assert_awaited_once_with(log_record, exc)

    # async def test_compute_rollover_handles_dst_properly_if_rollover_occurs_between_dst_change(
    #     self
    # ):
    #     handler = AsyncTimedRotatingFileHandler(
    #         filename=self.temp_file.name,
    #         when=RolloverInterval.MIDNIGHT,
    #         interval=1,
    #         backup_count=0,
    #         utc=False,
    #     )
    #
    #     # 2019-05-02 23:59:00 GMT
    #     current_time = 1_556_841_540
    #
    #     tm_year = 2019
    #     tm_mon = 5
    #     tm_mday = 3
    #     tm_hour = 0
    #     tm_min = 0
    #     tm_sec = 0
    #     tm_wday = 1
    #     tm_day = 122
    #     tm_isdst = 1
    #
    #     mocked_dst_time = (
    #         tm_year,
    #         tm_mon,
    #         tm_mday,
    #         tm_hour,
    #         tm_min,
    #         tm_sec,
    #         tm_wday,
    #         tm_day,
    #         tm_isdst,
    #     )
    #     with patch(
    #         "aiologger.handlers.files.time.localtime",
    #         side_effect=[time.localtime(current_time), mocked_dst_time],
    #     ):
    #         rollover_at = handler.compute_rollover(current_time)
    #         self.assertEqual()
    #         # ta dificil !
