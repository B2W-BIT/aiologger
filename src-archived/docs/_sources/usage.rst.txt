Usage
=====

``aiologger`` implements two different interfaces that you can use to
generate your logs. You can generate your logs using the ``async/await``
syntax or, if you for any reason can't (or don't want to) change all
your codebase to use this syntax you can use aiologger as if it were
synchronous, but behind the scenes your logs will be generated
asynchronously.

Migrating from standard lib logging
-----------------------------------

Using aiologger with the standard syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you prefer not to use the ``async/await`` all you need to do is to
replace you logger instance with an instance of ``aiologger.Logger``.
For now on you can call ``logger.info()`` the same way you are
(probably) already calling. Here is a simple example:

.. code:: python


   import asyncio
   import logging

   from logging import getLogger


   async def main():
       logger = getLogger(__name__)
       logging.basicConfig(level=logging.DEBUG, format="%(message)s")

       logger.debug("debug")
       logger.info("info")

       logger.warning("warning")
       logger.error("error")
       logger.critical("critical")


   loop = asyncio.get_event_loop()
   loop.run_until_complete(main())
   loop.run_forever()

Which will output the following lines:

::

   debug
   info
   warning
   error
   critical

--------------

If you want to generate all your logs asynchronously, you just have to
change the instance of the ``logger`` object. To do that, all we need to
change those lines from:

.. code:: python

   from logging import getLogger

   logger = getLogger(__name__)

to:

.. code:: python

   from aiologger import Logger

   logger = Logger.with_default_handlers()

and here is the complete example, generating all log lines
asynchronously.

.. code:: python

   import asyncio
   from aiologger import Logger


   async def main():
       logger = Logger.with_default_handlers(name='my-logger')

       logger.debug("debug")
       logger.info("info")

       logger.warning("warning")
       logger.error("error")
       logger.critical("critical")

       await logger.shutdown()


   loop = asyncio.get_event_loop()
   loop.run_until_complete(main())
   loop.run_forever()

This code will output the following lines:

::

   warning
   debug
   info
   error
   critical

As you might have noticed, the output order **IS NOT GUARANTEED**. If
some kind of order is important to you, you'll need to use the ``await``
syntax. But thinking about an asyncio application, where every I/O
operation is asynchronous, this shouldn't really matter.

Using aiologger with the async/await syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   import asyncio
   from aiologger import Logger


   async def main():
       logger = Logger.with_default_handlers(name='my-logger')

       await logger.debug("debug at stdout")
       await logger.info("info at stdout")

       await logger.warning("warning at stderr")
       await logger.error("error at stderr")
       await logger.critical("critical at stderr")

       await logger.shutdown()

   loop = asyncio.get_event_loop()
   loop.run_until_complete(main())
   loop.close()

The most basic use case is to log the output into ``stdout`` and
``stderr``. Using ``Logger.with_default_handlers`` you're able to
effortlessly create a new ``Logger`` instance with 2 distinct handlers:

-  One for handling ``debug`` and ``info`` methods and writing to
   ``stdout``;
-  The other, for handling ``warning``, ``critical``, ``exception`` and
   ``error`` methods and writing to ``stderr``.

Since everything is asynchronous, this means that for the same handler,
the output order is guaranteed, but not between distinct handlers. The
above code may output the following:

::

   warning at stderr
   debug at stdout
   error at stderr
   info at stdout
   critical at stderr

You may notice that the order between the same handler is guaranteed.
E.g.:

-  ``debug at stdout`` was outputted before ``info at stdout``
-  ``warning at stderr`` was outputted before ``error at stderr``
-  between lines of distinct handlers, the order isn't guaranteed.
   ``warning at stderr`` was outputted before ``debug at stdout``

Lazy initialization
~~~~~~~~~~~~~~~~~~~

Since the actual stream initialization only happens on the first log
call, it's possible to initialize ``aiologger.Logger`` instances outside
a running event loop:

.. code:: python


   import asyncio
   from aiologger import Logger


   async def main():
       logger = Logger.with_default_handlers(name='my-logger')

       await logger.debug("debug at stdout")
       await logger.info("info at stdout")

       await logger.warning("warning at stderr")
       await logger.error("error at stderr")
       await logger.critical("critical at stderr")

       await logger.shutdown()

   loop = asyncio.get_event_loop()
   loop.run_until_complete(main())
   loop.close()