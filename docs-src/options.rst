Options
~~~~~~~

- ``AIOLOGGER_HANDLE_ERROR_FALLBACK_ENABLED`` - An environment variable that tells aiologger whether it should emit a log to ``stderr`` in case of a handler emit raises an exceptions. To disable the default behaviour, set this environment variable to a falsy value ``("False", "false", "0")``. Default: True
