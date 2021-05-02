.. aiologger documentation master file, created by
   sphinx-quickstart on Thu Jan 31 17:38:35 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to aiologger docs!
=====================================

|PYPI| |PYPI Python Versions| |Build Status| |codecov| |black| |downloads|

.. |PYPI| image:: https://img.shields.io/pypi/v/aiologger.svg
   :target: http://pypi.python.org/pypi/aiologger
.. |PYPI Python Versions| image:: https://img.shields.io/pypi/pyversions/aiologger.svg
   :target: http://pypi.python.org/pypi/aiologger
.. |Build Status| image:: https://travis-ci.org/B2W-BIT/aiologger.svg?branch=master
   :target: https://travis-ci.org/B2W-BIT/aiologger
.. |codecov| image:: https://codecov.io/gh/B2W-BIT/aiologger/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/B2W-BIT/aiologger
.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black
.. |downloads| image:: https://pepy.tech/badge/aiologger
   :target: https://pepy.tech/project/aiologger


The builtin python logger is IO blocking. This means that using the
builtin ``logging`` module will interfere with your asynchronouns
application performance. ``aiologger`` aims to be the standard
Asynchronous non blocking logging for python and asyncio.

.. _GitHub: https://github.com/B2W-BIT/aiologger
.. _diogommartins: https://github.com/diogommartins
.. _daltonmatos: https://github.com/daltonmatos
.. _aiofiles: https://github.com/Tinche/aiofiles/tree/master/aiofiles



Installation
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install aiologger

Testing
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pipenv install --dev
   pipenv run test


Dependencies
~~~~~~~~~~~~~

- Python 3.6+
- *Optional*: aiofiles_ is required for file handlers

Authors and License
~~~~~~~~~~~~~~~~~~~~

The ``aiologger`` package is written mostly by diogommartins_ and daltonmatos_.

It's *MIT* licensed and freely available.

Feel free to improve this package and send a pull request to GitHub_.


A word about async, Python and files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tldr; ``aiologger`` is only fully async when logging to stdout/stderr. If you log into files on disk you are not being fully async and will be using Threads.

``aiologger`` was created when we realized that there were no async logging libs to use. At the time, Python's built-in logging infra-structure was fully sync (still is, 3.8 beta is out). That's why we created aiologger.

Despite everything (in Linux) being a file descriptor, a Network file descriptor and the stdout/stderr FDs are treated differently from files on disk FDs. This happens because there's no stable/usable async I/O interface published by the OS to be used by Python (or any other language). That's why **logging to files is NOT truly async**. ``aiologger`` implementation of file logging uses aiofiles_, which uses a Thread Pool to write the data. Keep this in mind when using ``aiologger`` for file logging.

Other than that, we hope ``aiologger`` helps you write fully async apps. :tada: :tada:

Table of Contents
=================

.. toctree::
   :maxdepth: 3

   usage
   loggers
   handlers
   options
   compatibility
   contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
