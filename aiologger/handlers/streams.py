import asyncio
import sys
from asyncio import AbstractEventLoop, StreamWriter
from typing import Union, Optional

from aiologger.filters import Filter
from aiologger.formatters.base import Formatter
from aiologger.handlers.base import Handler
from aiologger.levels import LogLevel
from aiologger.protocols import AiologgerProtocol
from aiologger.records import LogRecord


class AsyncStreamHandler(Handler):
    terminator = "\n"

    def __init__(
        self,
        stream=None,
        level: Union[str, int, LogLevel] = LogLevel.NOTSET,
        formatter: Formatter = None,
        filter: Filter = None,
        *,
        loop: Optional[AbstractEventLoop] = None,
    ) -> None:
        super().__init__(loop=loop)
        if stream is None:
            stream = sys.stderr
        self.stream = stream
        self.level = level
        if formatter is None:
            formatter = Formatter()
        self.formatter: Formatter = formatter
        if filter:
            self.add_filter(filter)
        self.protocol_class = AiologgerProtocol
        self._initialization_lock = None
        self.writer: Optional[StreamWriter] = None

    @property
    def initialized(self):
        return self.writer is not None

    async def _init_writer(self) -> StreamWriter:
        if self.initialized:
            return self.writer

        if not self._initialization_lock:
            self._initialization_lock = asyncio.Lock(loop=self.loop)

        async with self._initialization_lock:
            if self.writer is not None:
                return self.writer

            transport, protocol = await self.loop.connect_write_pipe(
                self.protocol_class, self.stream
            )

            self.writer = StreamWriter(  # type: ignore # https://github.com/python/typeshed/pull/2719
                transport=transport,
                protocol=protocol,
                reader=None,
                loop=self.loop,
            )
            return self.writer

    async def handle(self, record: LogRecord) -> bool:
        """
        Conditionally emit the specified logging record.
        Emission depends on filters which may have been added to the handler.
        """
        rv = self.filter(record)
        if rv:
            await self.emit(record)
        return rv

    async def flush(self):
        await self.writer.drain()

    async def emit(self, record: LogRecord):
        """
        Actually log the specified logging record to the stream.
        """
        if self.writer is None:
            self.writer = await self._init_writer()

        try:
            msg = self.formatter.format(record) + self.terminator

            self.writer.write(msg.encode())
            await self.writer.drain()
        except Exception as exc:
            await self.handle_error(record, exc)

    async def close(self):
        """
        Tidy up any resources used by the handler.

        This version removes the handler from an internal map of handlers,
        should ensure that this gets called from overridden close()
        methods.
        """
        if self.writer is None:
            return
        await self.flush()
        self.writer.close()
