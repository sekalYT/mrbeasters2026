"""
Шина событий Server-Sent Events (SSE) для мгновенного обновления интерфейса.
"""

import asyncio
from typing import Set
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()
_subscribers: Set[asyncio.Queue] = set()


async def broadcast_event(event_type: str, data: dict):
    """
    Отправка события всем подключенным веб-клиентам.
    """
    message = f"event: {event_type}\ndata: {data}\n\n"
    dead = set()
    for queue in _subscribers:
        try:
            queue.put_nowait(message)
        except Exception:
            dead.add(queue)
    _subscribers.difference_update(dead)


@router.get("/api/v1/events")
async def sse_events():
    """
    Эндпоинт потока SSE для живого обновления данных веб-панели без перезагрузки.
    """
    queue = asyncio.Queue()
    _subscribers.add(queue)

    async def event_generator():
        try:
            yield "event: connected\ndata: {\"status\": \"ok\"}\n\n"
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            pass
        finally:
            _subscribers.discard(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
