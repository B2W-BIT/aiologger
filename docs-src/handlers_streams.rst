Streams
=======

.. module:: aiologger.handlers.streams

AsyncStreamHandler
------------------

A handler class for writing logs into a stream which may be
``sys.stdout`` or ``sys.stderr``. If a stream isn't provided, it
defaults to ``sys.stderr``. If ``level`` is not specified,
``logging.NOTSET`` is used. If ``formatter`` is not ``None``, it is used
to format the log record before ``emit()`` gets called. A ``filter`` may
be used to filter log records

.. code:: python

   import sys
   from aiologger.handlers.streams import AsyncStreamHandler


   handler = AsyncStreamHandler(stream=sys.stdout)

It also accepts a level, formatter and filter at the initialization.