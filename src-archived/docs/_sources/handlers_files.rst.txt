Files
=======

.. module:: aiologger.handlers.files

AsyncFileHandler
----------------

**Important**: AsyncFileHandler depends on a optional dependency and you
should install aiologger with ``pip install aiologger[aiofiles]``

A handler class that sends logs into files. The specified file is opened
and used as the *stream* for logging. If ``mode`` is not specified, 'a'
is used. If ``encoding`` is not ``None``, it is used to open the file
with that encoding. The file opening is delayed until the first call to
``emit()``.

.. code:: python

   from aiologger.handlers.files import AsyncFileHandler
   from tempfile import NamedTemporaryFile


   temp_file = NamedTemporaryFile()
   handler = AsyncFileHandler(filename=temp_file.name)