import sys
import warnings
import functools
from asyncio import AbstractEventLoop
from typing import Callable, TypeVar, Type, cast


if sys.version_info >= (3, 7):
    from asyncio import get_running_loop
    from asyncio import create_task
else:
    from asyncio import _get_running_loop

    def get_running_loop():
        loop = _get_running_loop()
        if loop is None:
            raise RuntimeError("no running event loop")
        return loop

    def create_task(coro):
        loop = get_running_loop()
        return loop.create_task(coro)


_T = TypeVar("_T", bound=Type[object])


class _LoopCompat:
    __loop = None

    @property
    def _loop(self) -> AbstractEventLoop:
        warnings.warn(
            "The .loop and ._loop attributes are deprecated", DeprecationWarning
        )
        loop = self.__loop
        return get_running_loop() if loop is None else loop

    @property
    def loop(self) -> AbstractEventLoop:
        warnings.warn(
            "The .loop and ._loop attributes are deprecated", DeprecationWarning
        )
        return self._loop

    @classmethod
    def decorate(cls, v: _T) -> _T:
        @functools.wraps(v.__init__)
        def __init__(self, *args, **kwargs):
            try:
                self.__loop = kwargs.pop("loop")
            except KeyError:
                pass
            else:
                warnings.warn(
                    "The loop argument is deprecated", DeprecationWarning
                )
            __init__.__wrapped__(self, *args, **kwargs)

        v.__init__ = __init__  # type: ignore
        v.__loop = None  # type: ignore
        _loop = cls._loop
        loop = cls.loop
        if not hasattr(v, "_loop"):
            v._loop = _loop  # type: ignore

        if not hasattr(v, "loop"):
            v.loop = loop  # type: ignore

        return v


_F = TypeVar("_F", bound=Callable[..., object])

if sys.version_info >= (3, 10):

    def loop_compat(v: _T) -> _T:
        return v

    def bind_loop(v: _F, kwargs: dict) -> _F:
        return v


else:
    loop_compat = _LoopCompat.decorate

    def bind_loop(v: _F, kwargs: dict) -> _F:
        """
        bind a loop kwarg, without letting mypy know about it
        """
        try:
            return cast(_F, functools.partial(v, loop=kwargs["loop"]))
        except KeyError:
            pass
        return v


class classproperty:
    def __init__(self, func):
        self._func = func

    def __get__(self, obj, owner):
        return self._func(owner)


class CallableWrapper:
    def __init__(self, func: Callable) -> None:
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


if hasattr(sys, "_getframe"):
    get_current_frame = lambda: sys._getframe(3)
else:  # pragma: no cover

    def get_current_frame():
        """Return the frame object for the caller's stack frame."""
        try:
            raise Exception
        except Exception:
            return sys.exc_info()[2].tb_frame.f_back
