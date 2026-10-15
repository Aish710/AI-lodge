"""Run a CPU-heavy route body in a worker thread while watching for the client to disconnect.

If the client goes away (tab closed, request aborted, timeout) the running solve is told to stop, so the single solver slot frees within moments
instead of staying claimed until the solve's own time limit. If the stop signal is ever missed, the slot frees when that time limit ends."""
import asyncio

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from starlette.responses import Response

from app.optimiser.cancel import Cancelled, CancelToken, bind, unbind

POLL_SECONDS = 0.2
CLIENT_CLOSED = 499  # nobody receives it; it only shows in the access log


async def run_cancellable(request: Request, work):
    token = CancelToken()
    handle = bind(token)
    try:
        job = asyncio.ensure_future(run_in_threadpool(work))  # the task and its thread copy the context that holds the token
    finally:
        unbind(handle)
    try:
        while True:
            done, _ = await asyncio.wait({job}, timeout=POLL_SECONDS)
            if done:
                return job.result()
            if await request.is_disconnected():
                token.cancel()
                try:
                    await job
                except Cancelled:
                    pass
                return Response(status_code=CLIENT_CLOSED)
    except asyncio.CancelledError:  # the server cancelled this handler: still stop the solve
        token.cancel()
        raise
