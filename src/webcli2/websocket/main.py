#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
logger = logging.getLogger(__name__)

from typing import Optional, Tuple, Dict
import json
import asyncio
import time
from pydantic import BaseModel
from fastapi import WebSocket, WebSocketDisconnect
from webcli2.apilog import log_api_enter, log_api_exit

WEB_SOCKET_PING_INTERVAL = 20  # in seconds

class ClientInfo:
    queue: asyncio.Queue[Tuple[int, BaseModel]]
    websocket: WebSocket

    def __init__(self, client_id:str, websocket:WebSocket):
        self.client_id = client_id
        self.queue = asyncio.Queue()
        self.websocket = websocket
    
    async def pop_notification(self, timeout:float) -> Optional[Tuple[int, BaseModel]]:
        log_prefix = "ClientManager.pop_notification"
        log_api_enter(logger, log_prefix)

        try:
            # logger.debug(f"{log_prefix}: wait for notification, client_id={self.client_id}")
            r = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            # logger.debug(f"{log_prefix}: got notification, client_id={self.client_id}")
        except asyncio.TimeoutError:
            r = None
            # logger.debug(f"{log_prefix}: no notification for {self.client_id}")
        log_api_exit(logger, log_prefix)
        return r

class WebSocketConnectionManager:
    client_info_dict: Dict[str, ClientInfo]   # key is client_id
    lock: asyncio.Lock

    def __init__(self):
        self.lock = asyncio.Lock()
        self.client_info_dict = {}
    
    #######################################################################
    # Notify client via web socket that an action is completed
    #######################################################################
    async def publish_notification(self, client_id:str, action_id:int, response:BaseModel):
        log_prefix = "WebSocketConnectionManager.publish_notification"
        log_api_enter(logger, log_prefix)
        async with self.lock:
            client_info = self.client_info_dict.get(client_id)
            if client_info is None:
                logger.error(f"{log_prefix}: unable to publish notification, client_id={client_id}, action_id={action_id}, reason: invalid client_id")
            else:
                await client_info.queue.put((action_id, response))
                logger.debug(f"{log_prefix}: notification published to client, client_id={client_id}, action_id={action_id}")
        log_api_exit(logger, log_prefix)


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
        log_api_enter(logger, log_prefix)
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
                log_api_exit(logger, log_prefix)
                return

            ##########################################################################################
            # TODO
            # A client may get disconnected, and click "Connect" button from Web UI without
            # refreshing the browser and remain using the same client ID
            # We also need to prevent client from cheating us with a fake client_id and try to 
            # recevie notification for other client
            ##########################################################################################
            if client_id not in self.client_info_dict:
                self.client_info_dict[client_id] = ClientInfo(client_id, websocket)
            client_info = self.client_info_dict[client_id]
            logger.info(f"{log_prefix}: client({client_id}) is connected to websocket")
            
        try:
            last_ping_time:float = None
            while True:
                # need to ping client if needed
                now = time.time()
                if last_ping_time is None or now - last_ping_time >= WEB_SOCKET_PING_INTERVAL:
                    last_ping_time = now
                    await websocket.send_text("ping")

                r = await client_info.pop_notification(10)
                if r is None:
                    # no notification
                    continue

                action_id, response_model = r
                logger.debug(f"{log_prefix}: got notification, client_id={client_id}, action_id={action_id}")
                to_notify = {
                    "action_id": action_id,
                    "response": response_model.model_dump(mode="json")
                }
                await websocket.send_text(json.dumps(to_notify))
                logger.debug(f"{log_prefix}: notification passed to websocket, client_id={client_id}, action_id={action_id}")
        except WebSocketDisconnect:
            async with self.lock:
                if client_id in self.client_info_dict:
                    logger.debug(f"{log_prefix}: client({client_id}), websocket is disconnected and removed")
                    self.client_info_dict.pop(client_id)
                else:
                    # How come we cannot find this client_id from client_info_dict?
                    logger.error(f"{log_prefix}: client({client_id}), websocket is disconnected, we cannot find client_id, please investiage!")
        log_api_exit(logger, log_prefix)
