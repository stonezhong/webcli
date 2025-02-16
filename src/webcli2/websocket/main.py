#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
logger = logging.getLogger(__name__)

from typing import Optional, Dict, List
import enum
import json
import asyncio
import time
from pydantic import BaseModel
from fastapi import WebSocket, WebSocketDisconnect
from webcli2.apilog import log_api_enter, log_api_exit
from webcli2.webcli.output import CLIOutputChunk
from webcli2.exceptions import WebCLIException

WEB_SOCKET_PING_INTERVAL = 20  # in seconds

################################################
# Define notification exceptions
################################################
class NotificationError(WebCLIException):
    pass

class TopicAlreadyExist(NotificationError):
    topic_name:str

    def __init__(self, *args, topic_name:str):
        super().__init__(*args)
        self.topic_name = topic_name

class TopicNotFound(NotificationError):
    topic_name:str

    def __init__(self, *args, topic_name:str):
        super().__init__(*args)
        self.topic_name = topic_name

class TopicAlreadySubscribed(NotificationError):
    topic_name:str
    client_id:str

    def __init__(self, *args, topic_name:str, client_id:str):
        super().__init__(*args)
        self.topic_name = topic_name
        self.client_id = client_id

class TopicNotYetSubscribed(NotificationError):
    topic_name:str
    client_id:str

    def __init__(self, *args, topic_name:str, client_id:str):
        super().__init__(*args)
        self.topic_name = topic_name
        self.client_id = client_id

################################################
# Define various notification types
################################################
class NotificationType(enum.Enum):
    THREAD_STATUS_CHANGED   = "thread_status_changed"   # thread's title, description changed, thread's action order changed
    ACTION_STATUS_CHANGED   = "action_status_changed"   # an action's title, description, is_completed is changed
    NEW_ACTION_RESPONSE     = "new-action-response"     # an action got new response

class Notification(BaseModel):
    pass

class ActionOrderInfo(BaseModel):
    action_id: int
    display_order: int

class ActionStatusChanged(Notification):
    type: NotificationType = NotificationType.ACTION_STATUS_CHANGED
    action_id:int
    action_title:Optional[str] = None
    action_description:Optional[str] = None
    action_is_completed:Optional[bool] = None

class ThreadStatusChanged(Notification):
    type: NotificationType = NotificationType.THREAD_STATUS_CHANGED
    thread_id:int
    thread_title:str
    thread_description:str
    thread_action_orders: List[ActionOrderInfo]

class NewActionResponse(Notification):
    type: NotificationType = NotificationType.NEW_ACTION_RESPONSE
    action_id:int
    response_id:int
    chunk:CLIOutputChunk

################################################
# Define Subscriber and Topic class
################################################
class Subscriber:
    client_id: str
    queue: asyncio.Queue[Notification]

    def __init__(self, client_id:str):
        self.client_id = client_id
        self.queue = asyncio.Queue()

    async def pop_notification(self, timeout:float) -> Optional[Notification]:
        log_prefix = "Subscriber.pop_notification"
        # log_api_enter(logger, log_prefix)

        try:
            # logger.debug(f"{log_prefix}: wait for notification, client_id={self.client_id}")
            r = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            # logger.debug(f"{log_prefix}: got notification, client_id={self.client_id}")
        except asyncio.TimeoutError:
            r = None
            # logger.debug(f"{log_prefix}: no notification for {self.client_id}")
        # log_api_exit(logger, log_prefix)
        return r

class Topic:
    subscribers: Dict[str, Subscriber]
    lock: asyncio.Lock

    def __init__(self):
        self.subscribers = {}
        self.lock = asyncio.Lock()

################################################
# NotificationManager
################################################
class NotificationManager:
    topic_dict: Dict[str, Topic]
    lock: asyncio.Lock

    def __init__(self):
        self.lock = asyncio.Lock()
        self.topic_dict = {}

    ################################################################################################
    # subscribe a topic, if topic does not exist, create one
    ################################################################################################
    async def subscribe_topic(self, topic_name:str, subscriber:Subscriber):
        log_prefix = "NotificationManager.subscribe_topic"
        async with self.lock:
            if topic_name in self.topic_dict:
                topic = self.topic_dict[topic_name]
            else:
                topic = Topic()
                self.topic_dict[topic_name] = topic
                logger.info(f"{log_prefix}: topic({topic_name}) is created!")
            if subscriber.client_id in topic.subscribers:
                raise TopicAlreadySubscribed(topic_name=topic_name, client_id=subscriber.client_id)
            topic.subscribers[subscriber.client_id] = subscriber
            logger.info(f"{log_prefix}: topic({topic_name}) is subscribed by {subscriber.client_id}")

    async def unsubscribe_topic(self, topic_name:str, subscriber:Subscriber):
        async with self.lock:
            topic = self.topic_dict.get(topic_name)
            if topic is None:
                raise TopicNotFound(topic_name=topic_name)
            if subscriber.client_id not in topic.subscribers:
                raise TopicNotYetSubscribed(topic_name=topic_name, client_id=subscriber.client_id)
            topic.subscribers.pop(subscriber.client_id)

    async def publish_notification(self, topic_name:str, notification:Notification):
        log_prefix = "NotificationManager.publish_notification"
        for topic_name, topic in self.topic_dict.items():
            logger.info(topic.subscribers)

        async with self.lock:
            topic = self.topic_dict.get(topic_name)
            if topic is None:
                raise TopicNotFound(topic_name=topic_name)

        async with topic.lock:
            for _, subscriber in topic.subscribers.items():
                logger.info(f"{log_prefix}: topic_name={topic_name}, client_id={subscriber.client_id}")
                await subscriber.queue.put(notification)

    #######################################################################
    # This is called by web socket endpoint from fastapi
    # Here is an example
    #
    # @app.websocket("/ws")
    # async def websocket_endpoint(websocket: WebSocket):
    #     web_socket_connection_manager.websocket_endpoint(websocket)
    #
    #######################################################################
    async def websocket_endpoint(self, websocket: WebSocket):
        #######################################################################
        # Upon connection, client should send us a JSON object which contains
        # client_id and thread_id
        #######################################################################
        log_prefix = "websocket_endpoint"

        await websocket.accept()
        # client need to report it's client ID in the first place
        data = await websocket.receive_text() # TODO: need to specify a timeout for receive_text
        logger.debug(f"{log_prefix}: receive {data}")
        client_id:Optional[str] = None
        thread_id:Optional[int] = None
        try:
            json_data = json.loads(data)
            if isinstance(json_data, dict):
                client_id = json_data.get("client_id")
                if not isinstance(client_id, str):
                    client_id = None
                thread_id = json_data.get("thread_id")
                if not isinstance(thread_id, int):
                    thread_id = None
        except json.decoder.JSONDecodeError:
            pass

        if client_id is None or thread_id is None:
            logger.debug(f"{log_prefix}: client_id={client_id}, thread_id={thread_id}, missing client_id or thread_id from client")
            await websocket.close(code=1000, reason="Client ID or Thread ID not provided")
            return

        subscriber = Subscriber(client_id)
        topic_name = f"thread-{thread_id}"
        await self.subscribe_topic(topic_name, subscriber)
            
        try:
            #######################################################################
            # ping client periodically to make sure client is still connected
            #######################################################################
            last_ping_time:float = None
            while True:
                # need to ping client if needed
                now = time.time()
                if last_ping_time is None or now - last_ping_time >= WEB_SOCKET_PING_INTERVAL:
                    last_ping_time = now
                    await websocket.send_text("ping")

                notification = await subscriber.pop_notification(10)
                if notification is None:
                    # no notification
                    continue

                logger.debug(f"{log_prefix}: got notification, client_id={client_id}, thread_id={thread_id}")
                payload = notification.model_dump(mode="json")
                await websocket.send_text(json.dumps(payload))
                logger.debug(f"{log_prefix}: notification passed to websocket, client_id={client_id}, thread_id={thread_id}")
        except WebSocketDisconnect:
            self.unsubscribe_topic(topic_name, subscriber)
            logger.debug(f"{log_prefix}: client_id={client_id}, thread_id={thread_id}, unsubscribed")
            