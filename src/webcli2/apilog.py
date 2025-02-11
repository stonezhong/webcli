IGNORED_PREFIX = set([
    "WebCLIEngine.__init__",
    "WebCLIEngine.startup",
    "WebCLIEngine.shutdown",
    "PySparkActionHandler.startup",
    "PySparkActionHandler.listener",
    "ClientManager.publish_notification",
    "ClientManager.pop_notification",
    "WebSocketConnectionManager.publish_notification",
    "WebSocketConnectionManager.websocket_endpoint"
])

def log_api_enter(logger, log_prefix):
    if log_prefix in IGNORED_PREFIX:
        return
    logger.debug(f"{log_prefix}: enter")

def log_api_exit(logger, log_prefix):
    if log_prefix in IGNORED_PREFIX:
        return
    logger.debug(f"{log_prefix}: exit")
