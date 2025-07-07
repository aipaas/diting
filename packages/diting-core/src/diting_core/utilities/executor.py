#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from typing import Callable, Any


async def task_wrapper(
    sem: asyncio.Semaphore, func: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    async with sem:  # Acquire semaphore
        return await func(*args, **kwargs)
