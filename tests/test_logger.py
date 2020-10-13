import asyncio
import contextlib
import inspect
import unittest
import os
from typing import Tuple

import asynctest
from asynctest import CoroutineMock, Mock, patch, call, ANY

from aiologger.utils import get_running_loop
from aiologger.filters import StdoutFilter
from aiologger.handlers.streams import AsyncStreamHandler
from aiologger.levels import LogLevel
from aiologger.logger import Logger
from aiologger.records import LogRecord
from tests.utils import make_read_pipe_stream_reader


class LoggerOutsideEventLoopTest(unittest.TestCase):
    def test_property_loop_always_return_a_running_loop(self):
        logger = Logger(name="mylogger")

        # it's not safe to install the loop implictly, callers should use
        # asynio.run
        with self.assertRaises(RuntimeError):
            logger.loop

        # it's not safe to run the loop implictly, callers should use
        # asynio.run
        with contextlib.closing(asyncio.get_event_loop()) as loop:
            with self.assertRaises(RuntimeError):
                logger.loop

            results = []

            async def get_logger_loop():
                results.append(logger.loop)

            loop.run_until_complete(get_logger_loop())
            logger_loop, = results

            # now that the loop was explicitly set and started, we can use it
            self.assertIs(logger_loop, loop)
            del logger_loop
            self.assertFalse(loop.is_closed())

            # now that the loop was explicitly stopped, it's useless to return
            loop = asyncio.get_event_loop()
            with self.assertRaises(RuntimeError):
                logger.loop


class LoggerTests(asynctest.TestCase):
    async def setUp(self):
        r_fileno, w_fileno = os.pipe()
        self.read_pipe = os.fdopen(r_fileno, "r")
        self.write_pipe = os.fdopen(w_fileno, "w")

        patch("aiologger.logger.sys.stdout", self.write_pipe).start()
        patch("aiologger.logger.sys.stderr", self.write_pipe).start()

        self.stream_reader, self.reader_transport = await make_read_pipe_stream_reader(
            self.loop, self.read_pipe
        )

    def tearDown(self):
        self.read_pipe.close()
        self.write_pipe.close()
        self.reader_transport.close()
        patch.stopall()

    async def test_init_with_default_handlers_initializes_handlers_for_stdout_and_stderr(
        self
    ):
        handlers = [Mock(), Mock()]
        with asynctest.patch(
            "aiologger.logger.AsyncStreamHandler", side_effect=handlers
        ) as handler_init:
            logger = Logger.with_default_handlers(loop=self.loop)
            self.assertCountEqual(logger.handlers, handlers)

            self.assertCountEqual(
                [LogLevel.DEBUG, LogLevel.WARNING],
                [call[1]["level"] for call in handler_init.call_args_list],
            )

    async def test_init_with_default_handlers_initializes_handlers_with_proper_log_levels(
        self
    ):
        handlers = [Mock(), Mock()]
        with asynctest.patch(
            "aiologger.logger.AsyncStreamHandler", side_effect=handlers
        ) as init_from_pipe:
            logger = Logger.with_default_handlers()
            self.assertCountEqual(logger.handlers, handlers)

    async def test_callhandlers_calls_handlers_for_loglevel(self):
        level10_handler = Mock(level=10, handle=CoroutineMock())
        level30_handler = Mock(level=30, handle=CoroutineMock())

        logger = Logger.with_default_handlers()
        logger.handlers = [level10_handler, level30_handler]

        record = LogRecord(
            level=20,
            name="aiologger",
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None,
        )
        await logger.call_handlers(record)

        level10_handler.handle.assert_awaited_once_with(record)
        level30_handler.handle.assert_not_awaited()

    async def test_it_raises_an_error_if_no_handlers_are_found_for_record(self):
        logger = Logger.with_default_handlers()
        logger.handlers = []

        record = LogRecord(
            level=10,
            name="aiologger",
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None,
        )
        with self.assertRaises(Exception):
            await logger.call_handlers(record)

    async def test_it_calls_multiple_handlers_if_multiple_handle_matches_are_found_for_record(
        self
    ):
        level10_handler = Mock(level=10, handle=CoroutineMock())
        level20_handler = Mock(level=20, handle=CoroutineMock())

        logger = Logger.with_default_handlers()
        logger.handlers = [level10_handler, level20_handler]

        record = LogRecord(
            level=30,
            name="aiologger",
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None,
        )

        await logger.call_handlers(record)

        level10_handler.handle.assert_awaited_once_with(record)
        level20_handler.handle.assert_awaited_once_with(record)

    async def test_it_calls_handlers_if_logger_is_enabled_and_record_is_loggable(
        self
    ):
        logger = Logger.with_default_handlers()
        with patch.object(
            logger, "filter", return_value=True
        ) as filter, asynctest.patch.object(
            logger, "call_handlers"
        ) as callHandlers:
            record = Mock()
            await logger.handle(record)

            filter.assert_called_once_with(record)
            callHandlers.assert_awaited_once_with(record)

    async def test_it_doesnt_calls_handlers_if_logger_is_disabled(self):
        logger = Logger.with_default_handlers()
        with asynctest.patch.object(logger, "call_handlers") as callHandlers:
            record = Mock()
            logger.disabled = True
            await logger.handle(record)

            callHandlers.assert_not_awaited()

    async def test_it_doesnt_calls_handlers_if_record_isnt_loggable(self):
        logger = Logger.with_default_handlers()
        with patch.object(
            logger, "filter", return_value=False
        ) as filter, asynctest.patch.object(
            logger, "call_handlers"
        ) as callHandlers:
            record = Mock()
            await logger.handle(record)

            filter.assert_called_once_with(record)
            callHandlers.assert_not_awaited()

    async def test_log_makes_a_record_with_build_exc_info_from_exception(self):
        logger = Logger.with_default_handlers()
        try:
            raise ValueError("41 isn't the answer")
        except Exception as e:
            with patch.object(logger, "handle", CoroutineMock()) as handle:
                await logger._log(level=10, msg="Xablau", args=None, exc_info=e)
                call = handle.await_args_list.pop()
                record: LogRecord = call[0][0]
                exc_class, exc, exc_traceback = record.exc_info
                self.assertEqual(exc_class, ValueError)
                self.assertEqual(exc, e)

    async def test_log_makes_a_record_with_build_exc_info_from_sys_stack(self):
        logger = Logger.with_default_handlers()

        try:
            raise ValueError("41 isn't the answer")
        except Exception as e:
            with patch.object(logger, "handle", CoroutineMock()) as handle:
                await logger.exception("Xablau")

                call = handle.await_args_list.pop()
                record: LogRecord = call[0][0]
                exc_class, exc, exc_traceback = record.exc_info
                self.assertEqual(exc_class, ValueError)
                self.assertEqual(exc, e)

    async def test_it_logs_debug_messages(self):
        logger = Logger.with_default_handlers()
        await logger.debug("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_info_messages(self):
        logger = Logger.with_default_handlers()
        await logger.info("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_warning_messages(self):
        logger = Logger.with_default_handlers()
        await logger.warning("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_error_messages(self):
        logger = Logger.with_default_handlers()
        await logger.error("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_critical_messages(self):
        logger = Logger.with_default_handlers()
        await logger.critical("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_blocks_logs_with_level_lower_than_Logger_level(self):
        logger = Logger.with_default_handlers(level=LogLevel.CRITICAL)
        await logger.info("Xablau")

        self.assertEqual(len(self.stream_reader._buffer), 0)

    async def test_it_logs_exception_messages(self):
        logger = Logger.with_default_handlers()

        try:
            raise Exception("Xablau")
        except Exception:
            await logger.exception("Batemos tambores, eles panela.")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Batemos tambores, eles panela.\n")

        while self.stream_reader._buffer:
            logged_content += await self.stream_reader.readline()

        current_func_name = inspect.currentframe().f_code.co_name

        self.assertIn(current_func_name.encode(), logged_content)
        self.assertIn(b'raise Exception("Xablau")', logged_content)

    async def test_shutdown_doest_not_closes_handlers_if_not_initialized(self):
        initialized_handler = Mock(spec=AsyncStreamHandler)
        not_initialized_handler = Mock(
            spec=AsyncStreamHandler, initialized=False
        )

        logger = Logger()
        logger.handlers = [initialized_handler, not_initialized_handler]

        await logger.shutdown()

        initialized_handler.flush.assert_awaited_once()
        initialized_handler.close.assert_awaited_once()

        not_initialized_handler.flush.assert_not_awaited()
        not_initialized_handler.close.assert_not_awaited()

    async def test_shutdown_closes_all_handlers_if_initialized(self):
        handlers = [
            Mock(spec=AsyncStreamHandler),
            Mock(spec=AsyncStreamHandler),
        ]
        logger = Logger()
        logger.handlers = handlers

        await logger.shutdown()

        self.assertCountEqual(handlers, logger.handlers)

        for handler in logger.handlers:
            handler.flush.assert_awaited_once()
            handler.close.assert_awaited_once()

    async def test_shutdown_doest_not_closes_handlers_twice(self):
        handlers = [Mock(flush=CoroutineMock()), Mock(flush=CoroutineMock())]
        logger = Logger()
        logger.handlers = handlers

        await asyncio.gather(
            logger.shutdown(), logger.shutdown(), logger.shutdown()
        )

        self.assertCountEqual(handlers, logger.handlers)

        for handler in logger.handlers:
            handler.flush.assert_awaited_once()
            handler.close.assert_called_once()

    async def test_shutdown_ignores_erros(self):
        logger = Logger()
        logger.handlers = [
            Mock(flush=CoroutineMock(side_effect=ValueError)),
            Mock(flush=CoroutineMock()),
        ]

        await logger.shutdown()

        logger.handlers[0].close.assert_not_called()
        logger.handlers[1].close.assert_called_once()

    async def test_logger_handlers_are_not_initialized_twice(self):
        handler = Mock(spec=AsyncStreamHandler, level=LogLevel.DEBUG)
        with patch(
            "aiologger.logger.AsyncStreamHandler", return_value=handler
        ) as Handler:
            formatter = Mock()
            logger = Logger.with_default_handlers(formatter=formatter)
            await asyncio.gather(
                logger.info("sardinha"),
                logger.info("tilápia"),
                logger.info("xerelete"),
                logger.error("fraldinha"),
            )

            Handler.allert_has_calls(
                [
                    call(
                        stream=self.write_pipe,
                        level=LogLevel.DEBUG,
                        formatter=formatter,
                        filter=StdoutFilter(),
                    ),
                    call(
                        stream=self.write_pipe,
                        level=LogLevel.WARNING,
                        formatter=formatter,
                    ),
                ]
            )

            await logger.shutdown()

    async def test_it_returns_a_dummy_task_if_logging_isnt_enabled_for_level(
        self
    ):
        logger = Logger.with_default_handlers()
        self.assertIsNone(logger._dummy_task)

        with patch.object(
            logger, "is_enabled_for", return_value=False
        ) as isEnabledFor, patch.object(logger, "_dummy_task") as _dummy_task:
            log_task = logger.info("im disabled")
            isEnabledFor.assert_called_once_with(LogLevel.INFO)
            self.assertEqual(log_task, _dummy_task)

    async def test_it_returns_a_log_task_if_logging_is_enabled_for_level(self):
        logger = Logger.with_default_handlers()
        log_task = logger.info("Xablau")

        self.assertIsInstance(log_task, asyncio.Task)
        self.assertFalse(log_task.done())

        await log_task
        self.assertTrue(log_task.done())

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_only_keeps_a_reference_to_the_loop_after_the_first_log_call(
        self
    ):
        logger = Logger.with_default_handlers()
        self.assertIs(logger._loop, get_running_loop())

        await logger.info("Xablau")
        self.assertIs(logger._loop, get_running_loop())

    def test_find_caller_without_stack_info(self):
        logger = Logger()

        def caller_function():
            def log_function():
                def make_log_task():
                    return logger.find_caller()

                return make_log_task()

            return log_function()

        caller = caller_function()
        self.assertEqual(caller, (__file__, ANY, "caller_function", None))

    def test_find_caller_with_stack_info(self):
        logger = Logger()

        def caller_function():
            def log_function():
                def make_log_task():
                    try:
                        raise ValueError("Xablau!")
                    except Exception:
                        return logger.find_caller(True)

                return make_log_task()

            return log_function()

        caller = caller_function()

        self.assertEqual(caller.filename, __file__)
        self.assertEqual(caller.function_name, "caller_function")
        self.assertIn("return log_function()", caller.stack)

    def test_find_caller_without_current_frame_code(self):
        logger = Logger()

        with patch(
            "aiologger.logger.get_current_frame",
            return_value=Mock(f_back=object()),
        ):
            caller = logger.find_caller()

        self.assertEqual(caller.filename, "(unknown file)")
        self.assertEqual(caller.line_number, 0)
        self.assertEqual(caller.function_name, "(unknown function)")
        self.assertIsNone(caller.stack)

    def test_removehandler_removes_handler_if_handler_in_handlers(self):
        logger = Logger()
        handler = Mock()

        logger.handlers = [handler]

        logger.remove_handler(handler)
        self.assertEqual(logger.handlers, [])
