from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional


def schedule_background(coro: Awaitable, *, fallback: Optional[Callable[[], None]] = None) -> None:
    """
    Schedule the coroutine as a background task when an event loop is running; otherwise run the synchronous fallback.

    - coro: coroutine to run asynchronously
    - fallback: function to run when there is no event loop (optional)
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        if fallback is not None:
            fallback()
        else:
            # With no fallback, return silently; the caller decides what to do next
            return


