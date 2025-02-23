import logging
import logging
logger = logging.getLogger(__name__)

for logger_name in ["asyncio"]:
    logging.getLogger(logger_name).disabled = True

import asyncio
import pytest
from webcli2.core.service.notifications import NotificationManager, Notification, pop_notification


############################################################################
# Basic test
# step 1: client subscribe a topic
# step 2: someone publish a notification
# step 3: client gets the payload from the q associate with the subscription
############################################################################
@pytest.mark.asyncio
async def test_basic_subscribe_publish_01():
    await asyncio.sleep(0.5)
    nm = NotificationManager()

    ctx = {
        "client_ready": False,
        "notification_sent": False
    }
    async def client(foo):
        q = await nm.subscribe(topic_name="foo", client_id="client1")       
        ctx["client_ready"] = True
        event = await pop_notification(q, 5)
        assert event=={"xyz": 1}

    client_task = asyncio.create_task(client(1))
    while not ctx["client_ready"]:
        await asyncio.sleep(1)

    await nm.publish_notification(Notification(topic_name="foo", event={"xyz": 1}))
    await client_task

############################################################################
# Basic test
# step 1: client subscribe a topic
# step 2: client try to get payload but will cause timeout since no event has been published
############################################################################
@pytest.mark.asyncio
async def test_basic_subscribe_publish_02():
    await asyncio.sleep(0.5)
    nm = NotificationManager()

    async def client(foo):
        q = await nm.subscribe(topic_name="foo", client_id="client1")       
        event = await pop_notification(q, 5)
        assert event is None

    client_task = asyncio.create_task(client(1))
    await client_task

############################################################################
# Basic test
# step 1: client subscribe a topic
# step 2: client unsubscribe a topic
############################################################################
@pytest.mark.asyncio
async def test_basic_subscribe_unscribe_01():
    await asyncio.sleep(0.5)
    nm = NotificationManager()
    await nm.subscribe(topic_name="foo", client_id="client1")
    await nm.unsubscribe(topic_name="foo", client_id="client1")
    # once unsubscribed, empty topic will be removed
    assert "foo" not in nm.topics
