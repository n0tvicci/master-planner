import asyncio
import pytest
from backend.core.notifications import NotificationBus


@pytest.mark.asyncio
async def test_subscriber_receives_event():
    bus = NotificationBus()
    received = []

    async def collect():
        async for event in bus.subscribe():
            received.append(event)
            break  # collect one event then stop

    task = asyncio.create_task(collect())
    await asyncio.sleep(0)  # let subscriber register
    await bus.publish("step_complete", {"step": "topics"})
    await task

    assert len(received) == 1
    assert "step_complete" in received[0]


@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive():
    bus = NotificationBus()
    received_a = []
    received_b = []

    async def collect_a():
        async for event in bus.subscribe():
            received_a.append(event)
            break

    async def collect_b():
        async for event in bus.subscribe():
            received_b.append(event)
            break

    t1 = asyncio.create_task(collect_a())
    t2 = asyncio.create_task(collect_b())
    await asyncio.sleep(0)
    await bus.publish("test_event", {"x": 1})
    await t1
    await t2

    assert len(received_a) == 1
    assert len(received_b) == 1
