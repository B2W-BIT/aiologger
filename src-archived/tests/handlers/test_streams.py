import asyncio
import fcntl
import os
from unittest.mock import patch, Mock

import asynctest
from asynctest import CoroutineMock

from aiologger.handlers.streams import AsyncStreamHandler
from aiologger.protocols import AiologgerProtocol
from aiologger.records import LogRecord


class AsyncStreamHandlerTests(asynctest.TestCase):
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

        r_fileno, w_fileno = os.pipe()
        self.read_pipe = os.fdopen(r_fileno, "r")
        self.write_pipe = os.fdopen(w_fileno, "w")

    def tearDown(self):
        self.read_pipe.close()
        self.write_pipe.close()
        patch.stopall()

    def test_initialization(self):
        level = 40
        stream = Mock()
        formatter = Mock()
        filter = Mock()
        loop = Mock()
        handler = AsyncStreamHandler(
            stream, level, formatter, filter, loop=loop
        )

        self.assertIsInstance(handler, AsyncStreamHandler)

        self.assertEqual(handler.level, level)
        self.assertEqual(handler.formatter, formatter)
        self.assertEqual(handler.stream, stream)
        self.assertIn(filter, handler.filters)
        self.assertEqual(handler.loop, loop)

    async def test_init_gets_the_running_event_loop(self):
        handler = AsyncStreamHandler(
            stream=self.write_pipe, level=10, formatter=Mock()
        )

        self.assertIsInstance(handler.loop, asyncio.AbstractEventLoop)

    async def test_init_writer_makes_pipe_nonblocking(self):
        flags = fcntl.fcntl(self.write_pipe.fileno(), fcntl.F_GETFL)
        self.assertEqual(flags, 1)
        handler = AsyncStreamHandler(
            stream=self.write_pipe, level=10, formatter=Mock()
        )
        await handler._init_writer()

        flags = fcntl.fcntl(self.write_pipe.fileno(), fcntl.F_GETFL)
        self.assertEqual(flags, 1 | os.O_NONBLOCK)

        await handler.close()

    async def test_init_writer_initializes_a_nonblocking_pipe_streamwriter(
        self
    ):

        handler = AsyncStreamHandler(
            stream=self.write_pipe, level=10, formatter=Mock()
        )

        self.assertFalse(handler.initialized)

        await handler._init_writer()

        self.assertIsInstance(handler.writer, asyncio.StreamWriter)
        self.assertIsInstance(handler.writer._protocol, AiologgerProtocol)
        self.assertEqual(handler.writer.transport._pipe, self.write_pipe)
        self.assertTrue(handler.initialized)

        await handler.close()

    async def test_emit_writes_records_into_the_stream(self):
        msg = self.record.msg
        formatter = Mock(format=Mock(return_value=msg))
        writer = Mock(write=Mock(), drain=CoroutineMock())

        with patch(
            "aiologger.handlers.streams.StreamWriter", return_value=writer
        ):
            handler = AsyncStreamHandler(
                level=10, stream=self.write_pipe, formatter=formatter
            )

            await handler.emit(self.record)

            writer.write.assert_called_once_with(
                (msg + handler.terminator).encode()
            )
            writer.drain.assert_awaited_once()
            await handler.close()

    async def test_emit_calls_handle_error_if_an_error_occurs(self):
        writer = Mock(write=CoroutineMock(), drain=CoroutineMock())
        with patch(
            "aiologger.handlers.streams.StreamWriter", return_value=writer
        ):
            exc = Exception("XABLAU")
            handler = AsyncStreamHandler(
                level=10,
                stream=self.write_pipe,
                formatter=Mock(format=Mock(side_effect=exc)),
            )
            with asynctest.patch.object(
                handler, "handle_error"
            ) as handle_error:
                await handler.emit(self.record)

                handle_error.assert_awaited_once_with(self.record, exc)
                writer.write.assert_not_awaited()
                writer.drain.assert_not_awaited()

    async def test_handle_calls_emit_if_a_record_is_loggable(self):
        handler = AsyncStreamHandler(
            level=10, stream=Mock(), formatter=Mock(side_effect=Exception)
        )
        with asynctest.patch.object(handler, "emit") as emit, patch.object(
            handler, "filter", return_value=True
        ) as filter:
            self.assertTrue(await handler.handle(self.record))
            filter.assert_called_once_with(self.record)
            emit.assert_awaited_once_with(self.record)

        await handler.close()

    async def test_handle_doesnt_calls_emit_if_a_record_isnt_loggable(self):
        handler = AsyncStreamHandler(
            level=10, stream=Mock(), formatter=Mock(side_effect=Exception)
        )
        with asynctest.patch.object(handler, "emit") as emit, patch.object(
            handler, "filter", return_value=False
        ) as filter:
            self.assertFalse(await handler.handle(self.record))
            filter.assert_called_once_with(self.record)
            emit.assert_not_awaited()

    async def test_close_closes_the_underlying_transport(self):
        handler = AsyncStreamHandler(stream=self.write_pipe, level=10)
        await handler._init_writer()
        self.assertFalse(handler.writer.transport.is_closing())
        await handler.close()
        self.assertTrue(handler.writer.transport.is_closing())

    async def test_initialized_returns_true_if_writer_is_initialized(self):
        handler = AsyncStreamHandler(stream=self.write_pipe, level=10)
        self.assertFalse(handler.initialized)
        await handler._init_writer()
        self.assertTrue(handler.initialized)

    async def test_handle_error_writes_logs_to_stderr_if_emit_fails(self):
        handler = AsyncStreamHandler(
            level=10,
            stream=self.write_pipe,
            formatter=Mock(side_effect=Exception),
        )
        await handler._init_writer()
        exc = IOError("Something bad happened")
        with patch.object(handler.writer, "write", side_effect=exc), patch(
            "aiologger.handlers.base.sys.stderr"
        ) as stderr:
            await handler.handle(self.record)
            stderr.write.assert_called()

    async def test_handle_error_doesnt_writes_logs_to_stderr_if_emit_fails_and_fallback_is_disabled(
        self
    ):
        handler = AsyncStreamHandler(
            level=10,
            stream=self.write_pipe,
            formatter=Mock(side_effect=Exception),
        )
        await handler._init_writer()
        exc = IOError("Something bad happened")
        with patch.object(handler.writer, "write", side_effect=exc), patch(
            "aiologger.handlers.base.sys.stderr"
        ) as stderr, patch(
            "aiologger.handlers.base.settings.HANDLE_ERROR_FALLBACK_ENABLED",
            False,
        ):
            await handler.handle(self.record)
            stderr.write.assert_not_called()
