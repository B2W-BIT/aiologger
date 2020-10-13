# aiologger

[![PYPI](https://img.shields.io/pypi/v/aiologger.svg)](http://pypi.python.org/pypi/aiologger)
[![PYPI Python Versions](https://img.shields.io/pypi/pyversions/aiologger.svg)](http://pypi.python.org/pypi/aiologger)
[![Build Status](https://travis-ci.org/b2wdigital/aiologger.svg?branch=master)](https://travis-ci.org/b2wdigital/aiologger)
[![codecov](https://codecov.io/gh/b2wdigital/aiologger/branch/master/graph/badge.svg)](https://codecov.io/gh/b2wdigital/aiologger)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)


# About the Project

The builtin python logger is I/O blocking. This means that using the builtin
`logging` module will interfere with your asynchronouns application performance.
`aiologger` aims to be the standard Asynchronous non blocking logging for
python and asyncio.

# A word about async, Python and files

Tldr; `aiologger` is only fully async when logging to stdout/stderr. If you log into files on disk you are not being fully async and will be using Threads.

`aiologger` was created when we realized that there were no async logging libs to use. At the time, Python's built-in logging infra-structure was fully sync (still is, 3.8 beta is out). That's why we created aiologger.

Despite everything (in Linux) being a file descriptor, a Network file descriptor and the stdout/stderr FDs are treated differently from files on disk FDs. This happens because there's no stable/usable async I/O interface published by the OS to be used by Python (or any other language). That's why **logging to files is NOT truly async**. `aiologger` implementation of file logging uses [aiofiles](https://github.com/Tinche/aiofiles), which uses a Thread Pool to write the data. Keep this in mind when using `aiologger` for file logging.

Other than that, we hope `aiologger` helps you write fully async apps. :tada: :tada:


# Installation

```
pip install aiologger
```

# Testing

```
pipenv install --dev
pipenv run test
```

# Implemented interfaces

aiologger implements two different interfaces that you can use to generate your logs.
You can generate your logs using the `async/await` syntax or, if you for any reason can't (or don't want to)
change all your codebase to use this syntax you can use aiologger as if it were synchronous, but behind the scenes
your logs will be generated asynchronously.


# Migrating from standard lib logging


## Using aiologger with the standard syntax

If you prefer not to use the `async/await` all you need to do is to replace you logger instance with an instance of `aiologger.Logger`.
For now on you can call `logger.info()` the same way you are (probably) already calling. Here is a simple example:

```python

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


if __name__ == "__main__":
    asyncio.run(main())
```

Which will output the following lines:

```
debug
info
warning
error
critical
```

---

If you want to generate all your logs asynchronously, you just have to change the instance of the `logger` object.
To do that, all we need to change those lines from:

```python
from logging import getLogger

logger = getLogger(__name__)
```

to:

```python
from aiologger import Logger

logger = Logger.with_default_handlers()
```

and here is the complete example, generating all log lines asynchronously.

```python
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


if __name__ == "__main__":
    asyncio.run(main())
```

This code will output the following lines:

```
warning
debug
info
error
critical
```

As you might have noticed, the output order **IS NOT GUARANTEED**.
If some kind of order is important to you, you'll need to use the `await` syntax.
But thinking about an asyncio application, where every I/O operation is asynchronous,
this shouldn't really matter.

Also note that logger calls may only be made from an `async def` or from a
function called with an `async def` somewhere in the callstack.

## Using aiologger with the async/await syntax


```python
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

if __name__ == "__main__":
    asyncio.run(main())
```

The most basic use case is to log the output into `stdout` and `stderr`.
Using `Logger.with_default_handlers` you're able to effortlessly create a new
`Logger` instance with 2 distinct handlers:
* One for handling `debug` and `info` methods and writing to `stdout`;
* The other, for handling `warning`, `critical`, `exception` and `error` methods and writing to `stderr`.

Since everything is asynchronous, this means that for the same handler,
the output order is guaranteed, but not between distinct handlers.
The above code may output the following:

```
warning at stderr
debug at stdout
error at stderr
info at stdout
critical at stderr
```

You may notice that the order between the same handler is guaranteed. E.g.:
* `debug at stdout` was outputted before `info at stdout`
* `warning at stderr` was outputted before `error at stderr`
* between lines of distinct handlers, the order isn't guaranteed.
`warning at stderr` was outputted before `debug at stdout`

## Lazy initialization

Since the actual stream initialization only happens on the first log call, it's
possible to initialize `aiologger.Logger` instances outside a running event
loop:


```python

import asyncio
from aiologger import Logger


logger = Logger.with_default_handlers(name='my-logger')


async def main():

    await logger.debug("debug at stdout")
    await logger.info("info at stdout")

    await logger.warning("warning at stderr")
    await logger.error("error at stderr")
    await logger.critical("critical at stderr")

    await logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

# Loggers

## JsonLogger

A simple, featureful, drop-in replacement to the default `aiologger.Logger`
that grants to always log valid, single line, JSON output.

### It logs everything

```python
import asyncio
from datetime import datetime

from aiologger.loggers.json import JsonLogger


async def main():
    logger = JsonLogger.with_default_handlers()
    await logger.info("Im a string")
    # {"logged_at": "2018-06-14T09:34:56.482817", "line_number": 9, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": "Im a string"}

    await logger.info({
        'date_objects': datetime.now(),
        'exceptions': KeyError("Boooom"),
        'types': JsonLogger
    })
    # {"logged_at": "2018-06-14T09:34:56.483000", "line_number": 13, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": {"date_objects": "2018-06-14T09:34:56.482953", "exceptions": "Exception: KeyError('Boooom',)", "types": "<JsonLogger aiologger-json (DEBUG)>"}}

    await logger.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

### JsonLogger Options

`Callable[[], str]` log values may also be used to generate dynamic content that
are evaluated at serialization time. All you need to do is wrap the callable
using `CallableWrapper`:

```python
import asyncio
import logging
from random import randint

from aiologger.loggers.json import JsonLogger
from aiologger.utils import CallableWrapper


def rand():
    return randint(1, 100)


logger = JsonLogger.with_default_handlers(level=logging.DEBUG)


async def main():

    await logger.info(CallableWrapper(rand))
    # {"logged_at": "2018-06-14T09:37:52.624123", "line_number": 15, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": 70}

    await logger.info({"Xablau": CallableWrapper(rand)})
    # {"logged_at": "2018-06-14T09:37:52.624305", "line_number": 18, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": {"Xablau": 29}}

    await logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

###  Adding content to root

By default, everything passed to the log methods is inserted inside
the `msg` root attribute, but sometimes we want to add content to the root level.

#### Flatten

This behavior may be achieved using `flatten`. Which is
available both as a method parameter and instance attribute.

As an instance attribute, every call to a log method would "flat" the dict attributes.

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = JsonLogger.with_default_handlers(level=logging.DEBUG, flatten=True)

    await logger.info({"status_code": 200, "response_time": 0.00534534})
    # {"status_code": 200, "response_time": 0.534534, "logged_at": "2017-08-11T16:18:58.446985", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

    await logger.error({"status_code": 404, "response_time": 0.00134534})
    # {"status_code": 200, "response_time": 0.534534, "logged_at": "2017-08-11T16:18:58.446986", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

    await logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

As a method parameter, only the specific call would add the content to the root.

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=logging.DEBUG)

    await logger.info({"status_code": 200, "response_time": 0.00534534}, flatten=True)
    # {"logged_at": "2017-08-11T16:23:16.312441", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py", "status_code": 200, "response_time": 0.00534534}

    await logger.error({"status_code": 404, "response_time": 0.00134534})
    # {"logged_at": "2017-08-11T16:23:16.312618", "line_number": 8, "function": "<module>", "level": "ERROR", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py", "msg": {"status_code": 404, "response_time": 0.00134534}}

    await logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

**Warning**: It is possible to overwrite keys that are already present at root level.

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = JsonLogger.with_default_handlers(level=logging.DEBUG)

    await logger.info({'logged_at': 'Yesterday'}, flatten=True)
    # {"logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

    await logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

#### Extra

The `extra` parameter allow you to add specific content to root:


```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    a = 69
    b = 666
    c = [a, b]
    logger = JsonLogger.with_default_handlers(level=logging.DEBUG)

    await logger.info("I'm a simple log")
    # {"msg": "I'm a simple log", "logged_at": "2017-08-11T12:21:05.722216", "line_number": 5, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

    await logger.info({"dog": "Xablau"}, extra=locals())
    # {"logged_at": "2018-06-14T09:47:29.477705", "line_number": 14, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": {"dog": "Xablau"}, "logger": "<JsonLogger aiologger-json (DEBUG)>", "c": [69, 666], "b": 666, "a": 69}

    await logger.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

It also allows you to override the default root content:

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = JsonLogger.with_default_handlers(level=logging.DEBUG)

    await logger.info("I'm a simple log")
    # {"msg": "I'm a simple log", "logged_at": "2017-08-11T12:21:05.722216", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

    await logger.info("I'm a simple log", extra={'logged_at': 'Yesterday'})
    # {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

    await logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

and it may also be used as an instance attribute:

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = JsonLogger.with_default_handlers(level=logging.DEBUG, extra={'logged_at': 'Yesterday'})

    await logger.info("I'm a simple log")
    # {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

    await logger.info("I'm a simple log")
    # {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

    await logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```


#### Exclude default logger fields

If you think that the default fields are too much, it's also possible to
exclude fields from the output message.

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger
from aiologger.formatters.json import FUNCTION_NAME_FIELDNAME, LOGGED_AT_FIELDNAME


async def main():
    logger = JsonLogger.with_default_handlers(
        level=logging.DEBUG,
        exclude_fields=[FUNCTION_NAME_FIELDNAME,
                        LOGGED_AT_FIELDNAME,
                        'file_path',
                        'line_number']
    )

    await logger.info("Function, file path and line number wont be printed")
    # {"level": "INFO", "msg": "Function, file path and line number wont be printed"}

    await logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### Serializer options

`serializer_kwargs` is available both as instance attribute and as
a log method parameter and may be used to pass keyword arguments to the
`serializer` function. (See more: https://docs.python.org/3/library/json.html)

For pretty printing the output, you may use the `indent` kwarg. Ex.:

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = JsonLogger.with_default_handlers(
        level=logging.DEBUG,
        serializer_kwargs={'indent': 4}
    )

    await logger.info({
        "artist": "Black Country Communion",
        "song": "Cold"
    })

    await logger.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

Would result in a pretty indented output:

```javascript
{
    "logged_at": "2017-08-11T21:04:21.559070",
    "line_number": 5,
    "function": "<module>",
    "level": "INFO",
    "file_path": "/Users/diogo/Library/Preferences/PyCharm2017.1/scratches/scratch_32.py",
    "msg": {
        "artist": "Black Country Communion",
        "song": "Cold"
    }
}
```

The same result can be achieved making a log call with `serializer_kwargs`
as a parameter.


```python
await logger.warning({'artist': 'Black Country Communion', 'song': 'Cold'}, serializer_kwargs={'indent': 4})
```

# Handlers

## AsyncStreamHandler

A handler class for writing logs into a stream which may be `sys.stdout`
or `sys.stderr`. If a stream isn't provided, it defaults to `sys.stderr`. If
`level` is not specified, `logging.NOTSET` is used. If `formatter` is not
`None`, it is used to format the log record before `emit()` gets called. A
`filter` may be used to filter log records


```python
import sys
from aiologger.handlers.streams import AsyncStreamHandler


handler = AsyncStreamHandler(stream=sys.stdout)
```
It also accepts a level, formatter and filter at the initialization.

## AsyncFileHandler

**Important**: AsyncFileHandler depends on a optional dependency and you should
install aiologger with `pip install aiologger[aiofiles]`

A handler class that sends logs into files. The specified file is opened
and used as the _stream_ for logging. If `mode` is not specified, 'a' is
used. If `encoding` is not `None`, it is used to open the file with that
encoding. The file opening is delayed until the first call to `emit()`.

```python
from aiologger.handlers.files import AsyncFileHandler
from tempfile import NamedTemporaryFile


temp_file = NamedTemporaryFile()
handler = AsyncFileHandler(filename=temp_file.name)
```
# Options

* `AIOLOGGER_HANDLE_ERROR_FALLBACK_ENABLED` - An environment variable that tells
aiologger whether it should emit a log to `stderr` in case of a handler emit
raises an exceptions. To disable the default behaviour, set this
environment variable to a falsy value `("False", "false", "0")`. Default: `True`

# Compatibility

The explicit passing of a `loop` keyword argument, and subsequent access of a
`.loop` attribute, has been deprecated and will be removed in version 0.7.0 for
Loggers and Handlers.

Currently tested only on python 3.6 and 3.7

# Depencencies

Has none.
