import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator


class NotificationBus:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    async def publish(self, event_type: str, data: dict) -> None:
        payload = json.dumps(
            {
                "type": event_type,
                "data": data,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        for queue in self._subscribers:
            await queue.put(payload)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers.remove(queue)


notification_bus = NotificationBus()
