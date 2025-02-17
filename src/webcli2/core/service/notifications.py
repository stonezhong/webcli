import logging
logger = logging.getLogger(__name__)

from typing import Any, Dict, List

import asyncio

async def pop_notification(q:asyncio.Queue, timeout:float):
    try:
        r = await asyncio.wait_for(q.get(), timeout=timeout)
    except asyncio.TimeoutError:
        r = None
    return r

class Notification:
    topic_name:str
    event: Any

    def __init__(self, *, topic_name:str, event:Any):
        self.topic_name = topic_name
        self.event = event

class TopicInfo:
    subscribers: Dict[str, asyncio.Queue] # key is client id
    
    def __init__(self):
        self.subscribers = {}

class NotificationManager:
    lock: asyncio.Lock
    topics: Dict[str, TopicInfo]

    def __init__(self):
        self.lock = asyncio.Lock()
        self.topics = {}

    async def subscribe(self, topic_name:str, client_id:str) -> asyncio.Queue:
        log_prefix = "NotificationManager.subscribe"
        logger.debug(f"{log_prefix}: client({client_id}) subscribed topic({topic_name})")
        async with self.lock:
            if topic_name in self.topics:
                topic_info = self.topics[topic_name]
            if topic_name not in self.topics:
                topic_info = TopicInfo()
                self.topics[topic_name] = topic_info
            
            if client_id not in topic_info.subscribers:
                q = asyncio.Queue()
                topic_info.subscribers[client_id] = q
            else:
                q = topic_info.subscribers[client_id]
            return q

    async def unsubscribe(self, topic_name:str, client_id:str):
        log_prefix = "NotificationManager.unsubscribe"
        logger.debug(f"{log_prefix}: client({client_id}) unsubscribed topic({topic_name})")
        async with self.lock:
            if topic_name not in self.topics:
                logger.debug(f"{log_prefix}: topic not exist")
                return
            
            topic_info = self.topics[topic_name]
            if client_id not in topic_info.subscribers:
                return
            
            q = topic_info.subscribers.pop(client_id)
            q.shutdown()

            if len(topic_info.subscribers) == 0:
                self.topics.pop(topic_name)
                logger.debug(f"{log_prefix}: empty topic({topic_name}) is removed")


    async def publish_notification(self, notification:Notification):
        log_prefix = "NotificationManager.publish_notification"
        try:
            topic_name = notification.topic_name
            event = notification.event

            async with self.lock:
                if topic_name not in self.topics:
                    logger.debug(f"{log_prefix}: topic({topic_name}) does not exist, cannot publish nitification to it")
                    return
                
                topic_info = self.topics[topic_name]
                
                for client_id, q in topic_info.subscribers.items():
                    logger.debug(f"{log_prefix}: notify client({client_id}) on topic({topic_name})")
                    await q.put(event)
        except Exception:
            logger.exception("Unable to publish notification")


    async def publish_notifications(self, notifications:List[Notification]):
        log_prefix = "NotificationManager.publish_notifications"
        try:
            async with self.lock:
                for notification in notifications:
                    topic_name = notification.topic_name
                    event = notification.event

                    if topic_name not in self.topics:
                        logger.debug(f"{log_prefix}: topic({topic_name}) does not exist, cannot publish nitification to it")
                        return
                    
                    topic_info = self.topics[topic_name]
                    
                    for client_id, q in topic_info.subscribers.items():
                        logger.debug(f"{log_prefix}: notify client({client_id}) on topic({topic_name})")
                        await q.put(event)
        except Exception:
            logger.exception("Unable to publish notifications")

