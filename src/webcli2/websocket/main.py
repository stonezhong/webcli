#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
logger = logging.getLogger(__name__)

from typing import List, Optional, Tuple, Dict
import json
import asyncio
import time
from pydantic import BaseModel
from fastapi import WebSocket, WebSocketDisconnect

WEB_SOCKET_PING_INTERVAL = 20  # in seconds

class ClientManager:
    client_id: str
    lock: asyncio.Lock
    queue_dict: Dict[WebSocket, asyncio.Queue[Tuple[int, BaseModel]]]

    def __init__(self, client_id:str):
        self.client_id = client_id
        self.lock = asyncio.Lock()
        self.queue_dict = {}
    
    async def add_web_socket(self, websocket: WebSocket):
        async with self.lock:
            self.queue_dict[websocket] = asyncio.Queue()

    async def remove_web_socket(self, websocket: WebSocket) -> Optional[asyncio.Queue[Tuple[int, BaseModel]]]:
        async with self.lock:
            return self.queue_dict.pop(websocket, None)

    # send to all web socket for this client    
    async def publish_notification(self, action_id:int, response:BaseModel):
        log_prefix = "ClientManager.publish_notification"
        logger.debug(f"{log_prefix}: enter")
        for _, queue in self.queue_dict.items():
            await queue.put((action_id, response))
        logger.debug(f"{log_prefix}: notifiction has been pushed to {len(self.queue_dict)} queues")
        logger.debug(f"{log_prefix}: exit")
    
    async def pop_notification(self, websocket:WebSocket, timeout:float) -> Optional[Tuple[int, BaseModel]]:
        log_prefix = "ClientManager.pop_notification"
        # logger.debug(f"{log_prefix}: enter")
        async with self.lock:
            queue = self.queue_dict[websocket]
        try:
            r = await asyncio.wait_for(queue.get(), timeout=timeout)
            logger.debug(f"{log_prefix}: got notification for {self.client_id}")
        except asyncio.TimeoutError:
            r = None
            # logger.debug(f"{log_prefix}: no notification for {self.client_id}")
        # logger.debug(f"{log_prefix}: exit")
        return r

class WebSocketConnectionManager:
    client_manager_dict: Dict[str, ClientManager]   # key is client_id
    lock: asyncio.Lock

    def __init__(self):
        self.lock = asyncio.Lock()
        self.client_manager_dict = {}
    
    #######################################################################
    # Notify client via web socket that an action is completed
    #######################################################################
    async def publish_notification(self, client_id:str, action_id:int, response:BaseModel):
        log_prefix = "WebSocketConnectionManager.publish_notification"
        logger.debug(f"{log_prefix}: enter")
        async with self.lock:
            logger.debug(f"{log_prefix}: client_id={client_id}, action_id={action_id}")
            client_manager = self.client_manager_dict.get(client_id)
            if client_manager is None:
                logger.debug(f"{log_prefix}: invalid client_id")
            else:
                await client_manager.publish_notification(action_id, response)
        logger.debug(f"{log_prefix}: exit")


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
        log_prefix = "WebSocketConnectionManager.websocket_endpoint"
        
        logger.debug(f"{log_prefix}: enter")

        await websocket.accept()
        # client need to report it's client ID in the first place
        data = await websocket.receive_text()
        client_id = None
        try:
            json_data = json.loads(data)
            if isinstance(json_data, dict):
                client_id = json_data.get("client_id")
                if not isinstance(client_id, str):
                    client_id = None
        except json.decoder.JSONDecodeError:
            pass

        # TODO: improve, do not hold global lock
        async with self.lock:
            if client_id is None:
                logger.debug(f"{log_prefix}: client did not report client id, closing web socket")
                await websocket.close(code=1000, reason="Client ID not provided")
                logger.debug(f"{log_prefix}:  exit")
                return

            if client_id not in self.client_manager_dict:
                self.client_manager_dict[client_id] = ClientManager(client_id)
            client_manager = self.client_manager_dict[client_id]
            logger.debug(f"{log_prefix}: adding websocket {websocket} to client({client_id})")
            await client_manager.add_web_socket(websocket)
            
        try:
            last_ping_time:float = None
            while True:
                # need to ping client if needed
                now = time.time()
                if last_ping_time is None or now - last_ping_time >= WEB_SOCKET_PING_INTERVAL:
                    last_ping_time = now
                    await websocket.send_text("ping")

                r = await client_manager.pop_notification(websocket, 1.0)
                if r is None:
                    # no notification
                    continue

                action_id, response_model = r
                logger.debug(f"{log_prefix}: got notification, action_id={action_id}")
                to_notify = {
                    "action_id": action_id,
                    "response": response_model.model_dump(mode="json")
                }
                await websocket.send_text(json.dumps(to_notify))
                logger.debug(f"{log_prefix}: notification passed to websocket client")
        except WebSocketDisconnect:
            logger.error(f"{log_prefix}: web socket is disconnected")
            logger.debug(f"{log_prefix}: removing websocket {websocket} from client({client_id})")
            queue = await client_manager.remove_web_socket(websocket)
            if queue is None:
                logger.warning(f"{log_prefix}: cannot find websocket") # something is wrong, this should not happen
            else:
                logger.debug(f"{log_prefix}: cleint {client_id} has a websocket removed")
            
            async with self.lock:
                if len(client_manager.queue_dict) == 0:
                    self.client_manager_dict.pop(client_id)
                    logger.debug(f"{log_prefix}: cleint {client_id} is removed since no more websocket used by this client")

        logger.debug(f"{log_prefix}: exit")
