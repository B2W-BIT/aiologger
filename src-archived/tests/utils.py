import asyncio
from typing import Tuple

from aiologger.levels import LogLevel
from aiologger.records import LogRecord


def make_log_record(**kwargs) -> LogRecord:
    """
    Make a LogRecord whose attributes are defined by the specified kwargs
    """
    record = LogRecord(  # type: ignore
        name=None,
        level=LogLevel.NOTSET,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    )
    record.__dict__.update(kwargs)
    return record


async def make_read_pipe_stream_reader(
    loop, read_pipe
) -> Tuple[asyncio.StreamReader, asyncio.ReadTransport]:
    reader = asyncio.StreamReader(loop=loop)
    protocol = asyncio.StreamReaderProtocol(reader)

    transport, protocol = await loop.connect_read_pipe(
        lambda: protocol, read_pipe
    )
    return reader, transport
