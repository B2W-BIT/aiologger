import asyncio
import os
import unittest
from unittest.mock import patch

import uvloop

from aiologger import Logger


class UvloopIntegrationTests(unittest.TestCase):
    def setUp(self):
        r_fileno, w_fileno = os.pipe()
        self.read_pipe = os.fdopen(r_fileno, "r")
        self.write_pipe = os.fdopen(w_fileno, "w")

        patch("aiologger.logger.sys.stdout", self.write_pipe).start()
        patch("aiologger.logger.sys.stderr", self.write_pipe).start()

    def tearDown(self):
        self.read_pipe.close()
        self.write_pipe.close()
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
        patch.stopall()

    def test_it_logs_messages(self):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        loop = asyncio.get_event_loop()

        async def test():
            reader = asyncio.StreamReader(loop=loop)
            protocol = asyncio.StreamReaderProtocol(reader)

            transport, _ = await loop.connect_read_pipe(
                lambda: protocol, self.read_pipe
            )

            logger = Logger.with_default_handlers()
            await logger.info("Xablau")

            logged_content = await reader.readline()
            self.assertEqual(logged_content, b"Xablau\n")

            transport.close()
            await logger.shutdown()

        loop.run_until_complete(test())
